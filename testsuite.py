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
from backend.protocol_tools import run_protocol_test
import backend.util as util


class TestSuite:
    """
    A class to represent a test suite for SPARQL using QLever.

    Attributes:
        name (str): Name of the current run.
        path_to_binaries (str): Path to QLever binaries.
        path_to_testsuite (str): Path to the SPARQL test suite files.
        path_to_config (str): Path to the config file.
        file_name_for_tests (str): File name for the list of tests extracted from the test suite.
        command_index (str): Command used to index the graph with QLever.
        command_remove_index (str): Command used to remove the current index.
        command_start_server (str): Command used to start the Qlever server.
        command_stop_server (str): Command used to stop the Qlever server.
        server_address (str): Address of the QLever server ex. localhost.
        port (str): Port used for the QLever server.
        alias (dict): QLever specific datatypes ex. int = integer. Read from config.
        map_bnodes (dict): Dict to check if blank nodes are correct for every test.
        number_types (list): List with all types that are considered numbers. Read from config.
        directories (list): Contains all directories that will be considered when extracting tests.
        test_data (dict): Dictionary to store/log all the test data.
        tests_of_graph (dict): Dictionary grouping all tests using the same graph.
        tests (int): Total number of tests.
        passed (int): Number of passed tests.
        failed (int): Number of failed tests.
        passed_failed ( int): Number of tests that passed after using alias dict.
        self.path_to_test_suite (str): Path to the SPARQL Testsuite directory. Read from config.
    """

    def __init__(self, name: str, config: Config):
        """
        Constructs all the necessary attributes for the TestSuite object.

        Parameters:
            name (str): Name of the current run.
        """
        self.name = name
        self.config = config
        self.tests = {}
        self.test_count = 0
        self.passed = 0
        self.failed = 0
        self.passed_failed = 0

    def initialize_tests(self) -> bool:
        """
        Initialize tests from a specified CSV file.

        Reads the CSV file and processes each row.

        """
        for query in self.config.queries:
            self.tests[query.replace(".rq", "")] = {}
            file_name = query.replace(".rq", ".csv")
            if not util.path_exists("./tests/" + file_name):
                return False
            self.tests[query.replace(".rq", "")] = {}
            with open("./tests/" + file_name, "r", newline="") as csv_file:
                csv_reader = csv.reader(csv_file)
                for row in csv_reader:
                    self.process_row(row, self.tests[query.replace(".rq", "")])
        return True

    def process_row(self, row: list, graphs_list_of_tests: dict):
        """
        Process a single row of test data from the CSV file.

        Each row represents one test, build a TestObject with the data

        Parameters:
            row (list): A row from the CSV file representing a single test.
        """
        self.test_count += 1
        test = TestObject(row, self.config.path_to_test_suite, self.config)
        if test.graph == "":
            graph_path = "empty.ttl"
            if not os.path.exists(
                os.path.join(
                    self.config.path_to_test_suite,
                    graph_path)):
                open(
                    os.path.join(
                        self.config.path_to_test_suite,
                        graph_path),
                    'a').close()
        else:
            graph_path = os.path.join(test.group, test.graph)
        if graph_path in graphs_list_of_tests:
            graphs_list_of_tests[graph_path].append(test)
        else:
            graphs_list_of_tests[graph_path] = [test]

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
        setattr(test, "gotHtml", test_html)
        setattr(test, "expectedHtml", expected_html)
        setattr(test, "gotHtmlRed", test_red)
        setattr(test, "expectedHtmlRed", expected_red)

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
        self.log_for_all_tests([test], "errorType", error_type)

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
            graph_path: str,
            list_of_tests: list) -> bool:
        """
        Prepares the test environment for a given graph.

        Parameters:
            graph_path: The path to the graph file.

        Returns:
            True if the environment is successfully prepared, False otherwise.
        """
        status = False
        qlever.remove_index(self.config.command_remove_index)
        index = qlever.index(self.config.command_index, graph_path)
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
            self.log_for_all_tests(list_of_tests, "serverLog", server[1])
        self.log_for_all_tests(list_of_tests, "indexLog", index[1])
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
        setattr(test, "queryLog", query_log)
        self.update_test_status(test, FAILED, error_type)

    def run_query_tests(self, graphs_list_of_tests):
        """
        Executes query tests for each graph in the test suite.
        """
        for graph in graphs_list_of_tests:
            graph_path = os.path.join(self.config.path_to_test_suite, graph)
            print(f"Running query tests for graph: {graph_path}")

            if not self.prepare_test_environment(
                    graph_path, graphs_list_of_tests[graph]):
                continue

            for test in graphs_list_of_tests[graph]:
                result_format = test.result[test.result.rfind(".") + 1:]
                query_result = qlever.query(
                    test.queryFile,
                    "rq",
                    result_format,
                    self.config.server_address,
                    self.config.port)
                if query_result[0] == 200:
                    self.evaluate_query(
                        test.resultFile, query_result[1], test, result_format)
                else:
                    self.process_failed_response(test, query_result)

            qlever.stop_server(self.config.command_stop_server)
            if os.path.exists("./TestSuite.server-log.txt"):
                server_log = util.read_file("./TestSuite.server-log.txt")
                self.log_for_all_tests(
                    graphs_list_of_tests[graph],
                    "serverLog",
                    util.remove_date_time_parts(server_log))
            qlever.remove_index(self.config.command_remove_index)

    def run_update_tests(self, graphs_list_of_tests):
        """
        Executes update tests for each graph in the test suite.
        """
        for graph in graphs_list_of_tests:
            graph_path = os.path.join(self.config.path_to_test_suite, graph)
            print(f"Running update tests for graph: {graph_path}")
            for test in graphs_list_of_tests[graph]:
                if not self.prepare_test_environment(
                        graph_path, graphs_list_of_tests[graph]):
                    break
                result_format = test.result[test.result.rfind(".") + 1:]
                query_update_result = qlever.query(
                    test.queryFile,
                    "ru",
                    result_format,
                    self.config.server_address,
                    self.config.port)
                if query_update_result[0] == 200:
                    query_result_graph = qlever.query(
                        "CONSTRUCT {?s ?p ?o} WHERE {?s ?p ?o}",
                        "rq",
                        result_format,
                        self.config.server_address,
                        self.config.port)
                    if query_result_graph[0] == 200:
                        self.evaluate_query(
                            test.resultFile, query_result_graph[1], test, result_format)
                    else:
                        self.process_failed_response(test, query_result_graph)
                else:
                    self.process_failed_response(test, query_update_result)

                qlever.stop_server(self.config.command_stop_server)
                if os.path.exists("./TestSuite.server-log.txt"):
                    server_log = util.read_file("./TestSuite.server-log.txt")
                    self.log_for_all_tests(
                        graphs_list_of_tests[graph],
                        "serverLog",
                        util.remove_date_time_parts(server_log))
                qlever.remove_index(self.config.command_remove_index)

    def run_syntax_tests(self, graphs_list_of_tests):
        """
        Executes query tests for each graph in the test suite.
        """
        for graph in graphs_list_of_tests:
            graph_path = os.path.join(self.config.path_to_test_suite, graph)
            print(f"Running syntax tests for graph: {graph_path}")

            if not self.prepare_test_environment(
                    graph_path, graphs_list_of_tests[graph]):
                continue

            for test in graphs_list_of_tests[graph]:
                query_result = qlever.query(
                    test.queryFile,
                    "rq",
                    "srx",
                    self.config.server_address,
                    self.config.port)
                if query_result[0] != 200:
                    self.process_failed_response(test, query_result)
                else:
                    setattr(test, "queryLog", query_result[1])
                    self.update_test_status(test, PASSED, "")
                if test.typeName == "NegativeSyntaxTest11" or test.typeName == "NegativeUpdateSyntaxTest11":
                    if test.errorType == "QUERY EXCEPTION":
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
                    graphs_list_of_tests[graph],
                    "serverLog",
                    util.remove_date_time_parts(server_log))
            qlever.remove_index(self.config.command_remove_index)

    def get_comment(self, test: TestObject) -> tuple:
        qlever.remove_index(self.config.command_remove_index)
        index = qlever.index(
            self.config.command_index,
            os.path.join(
                self.config.path_to_test_suite,
                test.group,
                "manifest.ttl"))
        if not index[0]:
            return FAILED, INDEX_BUILD_ERROR, ""
        else:
            server = qlever.start_server(
                self.config.command_start_server,
                self.config.server_address,
                self.config.port)
            if not server[0]:
                return FAILED, SERVER_ERROR, ""
        query = f'PREFIX rdfs:    <http://www.w3.org/2000/01/rdf-schema#> PREFIX mf:      <http://www.w3.org/2001/sw/DataAccess/tests/test-manifest#>  SELECT ?comment WHERE {{ ?test mf:name """{test.name}""" . ?test rdfs:comment ?comment . }}'
        query_result = qlever.query(
            query,
            "rq",
            "srj",
            self.config.server_address,
            self.config.port)
        comment = json.loads(query_result[1])[
            "results"]["bindings"][0]["comment"]["value"]
        qlever.stop_server(self.config.command_stop_server)
        qlever.remove_index(self.config.command_remove_index)
        return PASSED, "", comment

    def run_protocol_tests(self, graphs_list_of_tests):
        """
        Executes protocol tests for each graph in the test suite.
        """
        for graph in graphs_list_of_tests:
            graph_path = os.path.join(self.config.path_to_test_suite, graph)
            print(f"Running protocol tests for graph: {graph_path}")

            for test in graphs_list_of_tests[graph]:
                status, error_type, comment = self.get_comment(test)
                if status == PASSED:
                    if not self.prepare_test_environment(
                            graph_path, graphs_list_of_tests[graph]):
                        break
                    status, error_type, extracted_expected_responses, extracted_sent_requests, got_responses = run_protocol_test(
                        test, comment, self.config.server_address, self.config.port)
                    qlever.stop_server(self.config.command_stop_server)
                    qlever.remove_index(self.config.command_remove_index)
                    if os.path.exists("./TestSuite.server-log.txt"):
                        server_log = util.read_file(
                            "./TestSuite.server-log.txt")
                        self.log_for_all_tests(
                            graphs_list_of_tests[graph],
                            "serverLog",
                            util.remove_date_time_parts(server_log))

                self.update_test_status(test, status, error_type)
                setattr(test, "protocol", comment)
                setattr(test, "protocolSent", extracted_sent_requests)
                setattr(
                    test,
                    "responseExtracted",
                    extracted_expected_responses)
                setattr(test, "response", got_responses)

    def run(self):
        """
        Main method to run all query tests.
        """
        self.run_query_tests(self.tests["Query"])
        self.run_query_tests(self.tests["Format"])
        self.run_update_tests(self.tests["Update"])
        self.run_syntax_tests(self.tests["Syntax"])
        self.run_protocol_tests(self.tests["Protocol"])
        self.run_protocol_tests(self.tests["GraphStoreProtocol"])

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
    if args[0] == "extract":
        if len(args) == 1:
            if config is None:
                return
            print(f"Extracting tests from test suite!")
            extract_tests(config)
        else:
            print(f"Usage to extract tests: python3 {sys.argv[0]} extract")
            return

    test_suite = TestSuite(args[0], config)
    if len(args) == 1 and args[0] != "config" and args[0] != "extract":
        if config is None:
            return
        if not test_suite.initialize_tests():
            return
        print("Run tests!")
        test_suite.run()
        test_suite.generate_json_file()
    elif args[0] != "config" and args[0] != "extract":
        print(f"  Usage to create config: python3 {sys.argv[0]} config <server address> <port> <path to testsuite> <path to binaries> <graph store implementation host> <path of the URL of the graph store> <URL returned in the Location HTTP header> \n  Usage to extract tests: python3 {sys.argv[0]} extract \n  Usage to run tests: python3 {sys.argv[0]} <name for the test suite run>")
        return
    print("Done!")


if __name__ == "__main__":
    main()
