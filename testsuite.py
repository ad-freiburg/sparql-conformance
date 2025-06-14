from typing import List, Dict, Tuple

import backend.config_manager as config_manager
import backend.qlever_manager as qlever
import os
import csv
import sys
import json
import bz2
from backend.models import TestObject, Config, SERVER_ERROR, FAILED, PASSED, INTENDED, QUERY_EXCEPTION, REQUEST_ERROR, UNDEFINED_ERROR, INDEX_BUILD_ERROR, SERVER_ERROR, NOT_TESTED, RESULTS_NOT_THE_SAME, INTENDED_MSG, EXPECTED_EXCEPTION, NOT_SUPPORTED
import backend.models as vars
from backend.extract_tests import extract_tests
from backend.xml_tools import compare_xml
from backend.tsv_csv_tools import compare_sv
from backend.json_tools import compare_json
from backend.rdf_tools import compare_ttl
from backend.protocol_tools import run_protocol_test, compare_response
import backend.util as util


class TestSuite:
    """
    A class to represent a test suite for SPARQL using QLever.
    """

    def __init__(self, name: str, tests: Dict[str, Dict[Tuple[Tuple[str, str], ...], List[TestObject]]], test_count, config: Config):
        """
        Constructs all the necessary attributes for the TestSuite object.

        Parameters:
            name (str): Name of the current run.
        """
        self.name = name
        self.config = config
        self.tests = tests
        self.test_count = test_count
        self.passed = 0
        self.failed = 0
        self.passed_failed = 0

    def evaluate_query(
            self,
            expected_string: str,
            query_result: str,
            test: TestObject,
            result_format: str):
        """
        Evaluates a query result based on the expected output and the format.

        Parameters:
            test (tuple): Information about the test being run.
            expected_output (str): The expected output of the query.
            query_result (str): The actual output received from the query.
            result_format (str): The format of the query output ("csv", "tsv", "srx", "srj").
        """
        status = FAILED
        error_type = RESULTS_NOT_THE_SAME
        if result_format == "srx":
            status, error_type, expected_html, test_html, expected_red, test_red = compare_xml(
                expected_string, query_result, self.config.alias, self.config.number_types)
        elif result_format == "srj":
            status, error_type, expected_html, test_html, expected_red, test_red = compare_json(
                expected_string, query_result, self.config.alias, self.config.number_types)
        elif (result_format == "csv" or result_format == "tsv"):
            status, error_type, expected_html, test_html, expected_red, test_red = compare_sv(
                expected_string, query_result, result_format, self.config.alias)
        elif result_format == "ttl":
            status, error_type, expected_html, test_html, expected_red, test_red = compare_ttl(
                expected_string, query_result)

        self.update_test_status(test, status, error_type)
        setattr(test, "got_html", test_html)
        setattr(test, "expected_html", expected_html)
        setattr(test, "got_html_red", test_red)
        setattr(test, "expected_html_red", expected_red)

    def evaluate_update(
                self,
                expected_graphs,
                graphs,
                test: TestObject):
        """
        Evaluates the graphs after running the update.

        Parameters:
            test (TestObject): Object containing the test being run.
            expected_graphs ([str]]): The expected state of each graph.
            graphs ([str]): The actual state of our graphs.
        """
        status = [FAILED for i in range(len(expected_graphs))]
        error_type = [RESULTS_NOT_THE_SAME for i in range(len(expected_graphs))]
        expected_html = ["" for i in range(len(expected_graphs))]
        test_html = ["" for i in range(len(expected_graphs))]
        expected_red = ["" for i in range(len(expected_graphs))]
        test_red = ["" for i in range(len(expected_graphs))]
        assert(len(expected_graphs) == len(graphs))
        for i in range(len(expected_graphs)):
            status[i], error_type[i], expected_html[i], test_html[i], expected_red[i], test_red[i] = compare_ttl(
                    expected_graphs[i], graphs[i])
            
        for s, e in zip(status, error_type):
            if s != PASSED:
                status[0] = s
                error_type[0] = e
                break
        
        self.update_test_status(test, status[0], error_type[0])
        t_html = f"<b>default:</b><br>{test_html[0]}"
        e_html = f"<b>default:</b><br>{expected_html[0]}"
        t_red = f"<b>default:</b><br>{test_red[0]}"
        e_red = f"<b>default:</b><br>{expected_red[0]}"
        i = 1
        for key, value in test.result_files.items():
            t_html += f"<br><br><b>{key}:</b><br>{test_html[i]}"
            e_html += f"<br><br><b>{key}:</b><br>{expected_html[i]}"
            t_red += f"<br><br><b>{key}:</b><br>{test_red[i]}"
            e_red += f"<br><br><b>{key}:</b><br>{expected_red[i]}"
            i += 1

        setattr(test, "got_html", t_html)
        setattr(test, "expected_html", e_html)
        setattr(test, "got_html_red", t_red)
        setattr(test, "expected_html_red", e_red)

    def log_for_all_tests(self, list_of_tests: list, attribute: str, log: str):
        """
        Logs information for all tests of a given graph.

        Parameters:
            graph_name (str): The graph.
            name (str): name .
            log (str): Log information from the server.
        """
        for test in list_of_tests:
            setattr(test, attribute, log)

    def update_test_status(
            self,
            test: TestObject,
            status: str,
            error_type: str):
        """
        Updates the status of a test in the test data.

        Parameters:
            test_name (str): The name of the test.
            status (str): The status of the test.
            error_type (str): The error message associated with the test.
        """
        self.log_for_all_tests([test], "status", status)
        self.log_for_all_tests([test], "error_type", error_type)

    def update_graph_status(
            self,
            list_of_tests: list,
            status: str,
            error_type: str):
        """
        Updates the status for all test of a graph.

        Parameters:
            graph_name (str): The name of the graph.
            status (str): The status of the graph.
            error_type (str): The error message associated with the graph.
        """
        for test in list_of_tests:
            self.update_test_status(test, status, error_type)

    def prepare_test_environment(
            self,
            graph_paths: Tuple[Tuple[str, str], ...],
            list_of_tests: list) -> bool:
        """
        Prepares the test environment for a given graph.

        Parameters:
            graph_paths: List containing the paths to the graph files.

        Returns:
            True if the environment is successfully prepared, False otherwise.
        """
        status = False
        qlever.remove_index(self.config.command_remove_index)
        index = qlever.index(self.config.command_index, graph_paths)
        if not index[0]:
            self.update_graph_status(list_of_tests, FAILED, INDEX_BUILD_ERROR)
            qlever.remove_index(self.config.command_remove_index)
        else:
            server = qlever.start_server(
                self.config.command_start_server,
                self.config.server_address,
                self.config.port)
            if not server[0]:
                self.update_graph_status(list_of_tests, FAILED, SERVER_ERROR)
            else:
                status = True
            self.log_for_all_tests(list_of_tests, "server_log", server[1])
        self.log_for_all_tests(list_of_tests, "index_log", index[1])
        return status

    def process_failed_response(self, test, query_response: tuple) -> tuple:
        if "exception" in query_response[1]:
            query_log = json.loads(
                query_response[1])["exception"].replace(
                ";", ";\n")
            error_type = QUERY_EXCEPTION
        elif "HTTP Request" in query_response[1]:
            error_type = REQUEST_ERROR
            query_log = query_response[1]
        elif "not supported" in query_response[1] and "content type" in query_response[1]:
            error_type = NOT_SUPPORTED
            query_log = query_response[1]
        else:
            error_type = UNDEFINED_ERROR
            query_log = query_response[1]
        setattr(test, "query_log", query_log)
        self.update_test_status(test, FAILED, error_type)

    def run_query_tests(self, graphs_list_of_tests):
        """
        Executes query tests for each graph in the test suite.
        """
        for graph in graphs_list_of_tests:
            print(f"Running query tests for graph / graphs: {graph}")
            if not self.prepare_test_environment(
                    graph, graphs_list_of_tests[graph]):
                continue

            for test in graphs_list_of_tests[graph]:
                query_result = qlever.query(
                    test.query_file,
                    "rq",
                    test.result_format,
                    self.config.server_address,
                    self.config.port)
                if query_result[0] == 200:
                    self.evaluate_query(
                        test.result_file, query_result[1], test, test.result_format)
                else:
                    self.process_failed_response(test, query_result)

            qlever.stop_server(self.config.command_stop_server)
            if os.path.exists("./TestSuite.server-log.txt"):
                server_log = util.read_file("./TestSuite.server-log.txt")
                self.log_for_all_tests(
                    graphs_list_of_tests[graph],
                    "server_log",
                    util.remove_date_time_parts(server_log))
            qlever.remove_index(self.config.command_remove_index)

    def run_update_tests(self, graphs_list_of_tests):
        """
        Executes update tests for each graph in the test suite.
        """
        for graph in graphs_list_of_tests:
            print(f"Running update tests for graph / graphs: {graph}")
            for test in graphs_list_of_tests[graph]:
                if not self.prepare_test_environment(
                        graph, graphs_list_of_tests[graph]):
                    # If the environment is not prepared, skip all tests for this graph.
                    break
                # Execute the update query.
                query_update_result = qlever.query(
                    test.query_file,
                    "ru",
                    test.result_format,
                    self.config.server_address,
                    self.config.port)
                
                # If the update query was successful, retrieve the current state of all graphs
                # and check if the results match the expected results.
                if query_update_result[0] == 200:
                    actual_state_of_graphs = []
                    expected_state_of_graphs = []
                    # Handle default graph that has no uri 
                    construct_graph = qlever.query(
                        "CONSTRUCT {?s ?p ?o} WHERE { GRAPH ql:default-graph {?s ?p ?o}}",
                        "rq",
                        "ttl",
                        self.config.server_address,
                        self.config.port)
                    actual_state_of_graphs.append(construct_graph[1])
                    expected_state_of_graphs.append(test.result_file)
                    
                    # Handle named graphs.
                    if test.result_files:
                        for graph_label, expected_graph in test.result_files.items():
                            construct_graph = qlever.query(
                                f"CONSTRUCT {{?s ?p ?o}} WHERE {{ GRAPH <{graph_label}> {{?s ?p ?o}}}}",
                                "rq",
                                "ttl",
                                self.config.server_address,
                                self.config.port)
                            actual_state_of_graphs.append(construct_graph[1])
                            expected_state_of_graphs.append(expected_graph)

                    # Evaluate state of graphs.
                    self.evaluate_update(expected_state_of_graphs, actual_state_of_graphs, test)
                else:
                    self.process_failed_response(test, query_update_result)

                qlever.stop_server(self.config.command_stop_server)
                if os.path.exists("./TestSuite.server-log.txt"):
                    server_log = util.read_file("./TestSuite.server-log.txt")
                    self.log_for_all_tests(
                        graphs_list_of_tests[graph],
                        "server_log",
                        util.remove_date_time_parts(server_log))
                qlever.remove_index(self.config.command_remove_index)

    def run_syntax_tests(self, graphs_list_of_tests: Dict[Tuple[Tuple[str, str], ...], List[TestObject]]):
        """
        Executes query tests for each graph in the test suite.
        """
        for graph_path in graphs_list_of_tests:
            print(f"Running syntax tests for graph: {graph_path}")
            if not self.prepare_test_environment(
                    graph_path, graphs_list_of_tests[graph_path]):
                continue

            for test in graphs_list_of_tests[graph_path]:
                content_type = "rq"
                result_format = "srx"
                if "Update" in test.type_name:
                    content_type = "ru"
                if "construct" in test.name:
                    result_format = "ttl"
                query_result = qlever.query(
                    test.query_file,
                    content_type,
                    result_format,
                    self.config.server_address,
                    self.config.port)
                if query_result[0] != 200:
                    self.process_failed_response(test, query_result)
                else:
                    setattr(test, "query_log", query_result[1])
                    self.update_test_status(test, PASSED, "")
                if test.type_name == "NegativeSyntaxTest11" or test.type_name == "NegativeUpdateSyntaxTest11":
                    if test.error_type == "QUERY EXCEPTION":
                        status = PASSED
                        error_type = ""
                    else:
                        status = FAILED
                        error_type = EXPECTED_EXCEPTION
                    self.update_test_status(test, status, error_type)

            qlever.stop_server(self.config.command_stop_server)
            if os.path.exists("./TestSuite.server-log.txt"):
                server_log = util.read_file("./TestSuite.server-log.txt")
                self.log_for_all_tests(
                    graphs_list_of_tests[graph_path],
                    "server_log",
                    util.remove_date_time_parts(server_log))
            qlever.remove_index(self.config.command_remove_index)

    def run_protocol_tests(self, graphs_list_of_tests: Dict[Tuple[Tuple[str, str], ...], List[TestObject]]):
        """
        Executes protocol tests for each graph in the test suite.
        """
        for graph_path in graphs_list_of_tests:
            print(f"Running protocol tests for graph: {graph_path}")
            # Work around for issue #25, missing data for protocol tests
            path_to_data = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
            graph_paths = graph_path
            for i in range(3):
                path_to_graph = os.path.join(path_to_data, f"data{i}.rdf")
                name_of_graph = f"http://kasei.us/2009/09/sparql/data/data{i}.rdf"
                new_path: Tuple[str, str] = (path_to_graph, name_of_graph)
                graph_paths = graph_paths + (new_path,)
            for test in graphs_list_of_tests[graph_path]:
                if not self.prepare_test_environment(
                        graph_paths, graphs_list_of_tests[graph_path]):
                    break
                if test.comment:
                    status, error_type, extracted_expected_responses, extracted_sent_requests, got_responses = run_protocol_test(
                        test, test.comment, self.config.server_address, self.config.port)
                    qlever.stop_server(self.config.command_stop_server)
                    qlever.remove_index(self.config.command_remove_index)
                    if os.path.exists("./TestSuite.server-log.txt"):
                        server_log = util.read_file(
                            "./TestSuite.server-log.txt")
                        self.log_for_all_tests(
                            graphs_list_of_tests[graph_path],
                            "server_log",
                            util.remove_date_time_parts(server_log))

                    self.update_test_status(test, status, error_type)
                else:
                    extracted_sent_requests = ''
                    extracted_expected_responses = ''
                    got_responses = ''
                setattr(test, "protocol", test.comment)
                setattr(test, "protocol_sent", extracted_sent_requests)
                setattr(
                    test,
                    "response_extracted",
                    extracted_expected_responses)
                setattr(test, "response", got_responses)

    def run(self):
        """
        Main method to run all query tests.
        """
        self.run_query_tests(self.tests["query"])
        self.run_query_tests(self.tests["format"])
        self.run_update_tests(self.tests["update"])
        self.run_syntax_tests(self.tests["syntax"])
        self.run_protocol_tests(self.tests["protocol"])
        self.run_protocol_tests(self.tests["graphstoreprotocol"])

    def compress_json_bz2(self, input_data, output_filename):
        with bz2.open(output_filename, "wt") as zipfile:
            json.dump(input_data, zipfile, indent=4)
        print("Done writing result file: " + output_filename)

    def generate_json_file(self):
        """
        Generates a JSON file with the test results.
        """
        os.makedirs("./results", exist_ok=True)
        file_path = f"./results/{self.name}.json.bz2"
        data = {}

        for test_format in self.tests:
            for graph in self.tests[test_format]:
                for test in self.tests[test_format][graph]:
                    match test.status:
                        case vars.PASSED:
                            self.passed += 1
                        case vars.FAILED:
                            self.failed += 1
                        case vars.INTENDED:
                            self.passed_failed += 1
                    # This will add a number behind the name if the name is not
                    # unique
                    if test.name in data:
                        i = 1
                        while True:
                            i += 1
                            new_name = f"{test.name} {i}"
                            if new_name in data:
                                continue
                            else:
                                test.name = new_name
                                data[new_name] = test.to_dict()
                                break
                    else:
                        data[test.name] = test.to_dict()
        data["info"] = {
            "name": "info",
            "passed": self.passed,
            "tests": self.test_count,
            "failed": self.failed,
            "passedFailed": self.passed_failed,
            "notTested": (
                self.test_count -
                self.passed -
                self.failed -
                self.passed_failed)}
        print("Writing file...")
        self.compress_json_bz2(data, file_path)

def main():
    args = sys.argv[1:]
    if len(args) < 1:
        print(f"  Usage to create config: python3 {sys.argv[0]} config <server address> <port> <path to testsuite> <path to the qlever binaries>  <graph store implementation host> <path of the URL of the graph store> <URL returned in the Location HTTP header>\n  Usage to extract tests: python3 {sys.argv[0]} extract \n  Usage to run tests: python3 {sys.argv[0]} <name for the test suite run>")
        return

    if args[0] == "config":
        if len(args) == 8:
            print(f"Create basic config.")
            config_manager.create_config(
                args[1], args[2], args[3], args[4], args[5], args[6], args[7])
        else:
            print(
                f"Usage to create config: python3 {sys.argv[0]} config <server address> <port> <path to testsuite> <path to the qlever binaries> <graph store implementation host> <path of the URL of the graph store> <URL returned in the Location HTTP header>")
            return

    config = config_manager.initialize_config()

    if len(args) == 1 and args[0] != "config" and args[0] != "extract":
        if config is None:
            return
        print("Read tests!")
        tests, test_count = extract_tests(config)
        test_suite = TestSuite(args[0], tests, test_count, config)
        print("Run tests!")
        test_suite.run()
        test_suite.generate_json_file()
    elif args[0] != "config" and args[0] != "extract":
        print(f"  Usage to create config: python3 {sys.argv[0]} config <server address> <port> <path to testsuite> <path to binaries> <graph store implementation host> <path of the URL of the graph store> <URL returned in the Location HTTP header> \n  Usage to extract tests: python3 {sys.argv[0]} extract \n  Usage to run tests: python3 {sys.argv[0]} <name for the test suite run>")
        return
    print("Done!")
    return



if __name__ == "__main__":
    main()
