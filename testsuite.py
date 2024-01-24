import os
import sys
import time
import csv
import requests
import json
import subprocess
import json
import re
import xml.etree.ElementTree as ET
from io import StringIO
from xml.sax.saxutils import escape

class TestSuite:
    """
    A class to represent a test suite for SPARQL using QLever.

    Attributes:
        name (str): Name of the current run.
        path_to_binaries (str): Path to QLever binaries.
        alias (dict): QLever specific datatypes ex. int = integer. Read from config.
        map_bnodes (dict): Dict to check if blank nodes are correct for every test.
        number_types (list): List with all types that are considered numbers. Read from config.
        test_data (dict): Dictionary to store/log all the test data.
        tests_of_graph (dict): Dictionary grouping all tests using the same graph.
        tests (int): Total number of tests.
        passed (int): Number of passed tests.
        failed (int): Number of failed tests.
        passed_failed ( int): Number of tests that passed after using alias dict.
        self.path_to_test_suite (str): Path to the SPARQL Testsuite directory. Read from config.
    """

    def __init__(self, path: str, name: str):
        """
        Constructs all the necessary attributes for the TestSuite object.

        Parameters:
            path (str): Path to QLever binaries.
            name (str): Name of the current run.
        """
        self.name = name
        self.path_to_binaries = path
        self.alias = {}
        self.map_bnodes = {}
        self.number_types = []
        self.test_data = {}
        self.tests_of_graph = {}
        self.tests = 0
        self.passed = 0
        self.failed = 0
        self.passed_failed = 0
        self.path_to_test_suite = ""

    def initialize_tests(self, file: str):
        """
        Initialize tests from a specified CSV file.

        Reads the CSV file and processes each row.

        Parameters:
            file (str): Path to the CSV file containing test definitions.
        """
        if not os.path.exists(file):
            print(f"{file} does not exist!")
            return

        with open(file, "r", newline="") as csv_file:
            csv_reader = csv.reader(csv_file)
            for row in csv_reader:
                self.process_row(row)

    def initialize_config(self):
        """
        Initialize config file.

        Check if config exists and initialize content:
          if not: create basic config file
        """
        path_to_config = "./config.json"
        if not os.path.exists(path_to_config):
            print(f"{path_to_config} does not exist!")
            print(f"Create basic {path_to_config}")
            config = {
                    "path_to_testsuite": "./testsuite/",
                    "alias": {            
                            "http://www.w3.org/2001/XMLSchema#integer": "http://www.w3.org/2001/XMLSchema#int",
                            "http://www.w3.org/2001/XMLSchema#double": "http://www.w3.org/2001/XMLSchema#decimal",
                            "http://www.w3.org/2001/XMLSchema#int": "http://www.w3.org/2001/XMLSchema#integer",
                            "http://www.w3.org/2001/XMLSchema#decimal": "http://www.w3.org/2001/XMLSchema#double",
                            "http://www.w3.org/2001/XMLSchema#string": None
                            },
                    "number_types": [
                                    "http://www.w3.org/2001/XMLSchema#integer",
                                    "http://www.w3.org/2001/XMLSchema#double",
                                    "http://www.w3.org/2001/XMLSchema#decimal",
                                    "http://www.w3.org/2001/XMLSchema#float",
                                    "http://www.w3.org/2001/XMLSchema#int",
                                    "http://www.w3.org/2001/XMLSchema#decimal"
                                    ]
                      }
            self.alias = config["alias"]
            self.number_types = config["number_types"]
            self.path_to_test_suite = config["path_to_testsuite"]
            with open(path_to_config, "w") as file:
                    json.dump(config, file, indent=4)
            return
        
        with open(path_to_config, "r") as file:
            config = json.load(file)
            self.alias = config["alias"]
            self.number_types = config["number_types"]
            self.path_to_test_suite = config["path_to_testsuite"]

    def process_row(self, row: list):
        """
        Process a single row of test data from the CSV file.

        Pu the test data into the test_data dict.

        Parameters:
            row (list): A row from the CSV file representing a single test.
        """
        self.tests += 1
        path_to_test, graph_path, type_of_test = self.extract_test_details(row)

        if type_of_test in ["QueryEvaluationTest", "CSVResultFormatTest", "PositiveSyntaxTest11", "NegativeSyntaxTest11"]:
            self.handle_special_test_types(row, type_of_test)
            if graph_path in self.tests_of_graph:
                self.tests_of_graph[graph_path].append([row[7], row[9], row[2], type_of_test])
            else:
                self.tests_of_graph[graph_path] = [[row[7], row[9], row[2], type_of_test]]

        self.test_data[row[2]] = self.construct_test_data(row, path_to_test, type_of_test)

    def extract_test_details(self, row: list) -> tuple:
        """
        Returns the test details from a CSV row.

        Parameters:
            row (list): A row from the CSV file.

        Returns:
            tuple: A tuple containing the path to the test, path to the graph and the type of the test.
        """
        last_slash_index = row[0].rfind("/")
        second_last_slash_index = row[0].rfind("/", 0, last_slash_index - 1)
        path_to_test = row[0][second_last_slash_index + 1: last_slash_index + 1]

        last_hashtag_index = row[1].rfind("#")
        type_of_test = row[1][last_hashtag_index + 1:]
        
        graph_path = path_to_test + row[8]
        return path_to_test, graph_path, type_of_test

    def handle_special_test_types(self, row: list, type_of_test: str):
        """
        Handles special types of tests and modifies the row data accordingly.

        Parameters:
            row (list): A row from the CSV file.
            type_of_test (str): The type of the test.
        """
        if type_of_test in ["PositiveSyntaxTest11", "NegativeSyntaxTest11"]:
            row[8] = row[8] if row[8] else "manifest.ttl"
            row[7] = row[7] if row[7] else row[11]

    def construct_test_data(self, row: list, path_to_test: str, type_of_test: str) -> dict:
        """
        Constructs a dictionary of test data from a CSV row.

        Parameters:
            row (list): A row from the CSV file.
            path_to_test (str): The path to the test.
            type_of_test (str): The type of the test.

        Returns:
            dict: A dictionary containing detailed test data.
        """
        test_data = {
            "test": row[0],
            "type": row[1],
            "typeName": type_of_test,
            "name": row[2],
            "path": path_to_test,
            "group": path_to_test[:-1],
            "feature": row[3],
            "comment": row[4],
            "approval": row[5],
            "approvedBy": row[6],
            "query": row[7],
            "graph": row[8],
            "result": row[9],
            "queryFile": self.read_file(self.path_to_test_suite + path_to_test + row[7]),
            "graphFile": self.read_file(self.path_to_test_suite + path_to_test + row[8]),
            "resultFile": self.read_file(self.path_to_test_suite + path_to_test + row[9]),
            "status": "Not tested",
            "errorType": "",
            "expectedHtml": "",
            "gotHtml": "",
            "indexLog": "",
            "serverLog": "",
            "serverStatus": "",
            "queryLog": "",
            "querySent": "",
            "updateGraph": row[15] if len(row) > 15 else "",
            "updateGraphFile": self.read_file(self.path_to_test_suite + path_to_test + row[15]) if len(row) > 15 else "",
            "updateLabel": row[17] if len(row) > 17 else "",
            "updateRequest": row[13] if len(row) > 13 else "",
            "updateRequestFile": self.read_file(self.path_to_test_suite + path_to_test + row[13]) if len(row) > 13 else "",
            "updateResult": row[16] if len(row) > 16 else "",
            "updateResultFile": self.read_file(self.path_to_test_suite + path_to_test + row[16]) if len(row) > 16 else ""
        }
        return test_data
    
    def read_file(self, file_path: str) -> str:
        """
        Reads and returns the content of a file.
        
        If file does not exist return empty string.
        Parameters:
            file_path (str): The path to the file to be read.

        Returns:
            str: The content of the file.
        """
        try:
            data = open(file_path).read()
        except:
            data = ""
        return data

    def index(self, graph_path: str) -> str:
        """
        Executes a command to index a graph file using the IndexBuilderMain binary.

        Parameters:
            graph_path (str): The path to the graph file to be indexed.

        Returns:
            str: The output of the indexing process if successful or an error message if the process fails.

        Raises:
            Exception: If any exception occurs during the indexing process it is caught and an error message is returned.
        """
        try:
            cmd = f"ulimit -Sn 1048576; cat {graph_path} | {self.path_to_binaries}/IndexBuilderMain -F ttl -f - -i TestSuite -s TestSuite.settings.json | tee TestSuite.index-log.txt"
            process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            output, error = process.communicate()
            if process.returncode != 0:
                return f"Indexing error: {error.decode('utf-8')}"
            return output.decode("utf-8")
        except Exception as e:
            return f"Exception during indexing: {str(e)}"

    def remove_index(self):
        """
        Removes index and related files for the TestSuite.

        Raises:
            subprocess.CalledProcessError: If an error occurs during the file deletion process.
        """
        try:
            subprocess.check_call("rm -f TestSuite.index.* TestSuite.vocabulary.* TestSuite.prefixes TestSuite.meta-data.json TestSuite.index-log.txt", shell=True)
        except subprocess.CalledProcessError as e:
            print(f"Error removing index files: {e}")

    def start_server(self):
        """
        Starts the SPARQL server and waits for it to be ready.


        Returns:
            tuple: A tuple containing the HTTP status code and a message indicating the server startup status.

        Raises:
            Exception: If any exception occurs during the server startup process.
        """
        try:
            cmd = f"{self.path_to_binaries}/ServerMain -i TestSuite -j 8 -p 7001 -m 4 -c 2 -e 1 -k 100 -a 'TestSuite_3139118704' > TestSuite.server-log.txt &"
            subprocess.Popen(cmd, shell=True)

            return self.wait_for_server_startup()
        except Exception as e:
            return (500, f"Exception during server start: {str(e)}")

    def wait_for_server_startup(self):
        """
        Waits for the SPARQL server to start up.

        This method makes repeated attempts to send a test query to the server. If the server
        responds successfully within the maximum number of retries, it is considered operational.

        Returns:
            tuple: A tuple containing the HTTP status code and a message indicating the server status.
        """
        max_retries = 8
        retry_interval = 0.25
        url = "http://mint-work:7001"
        headers = {"Content-type": "application/sparql-query"}
        test_query = "SELECT ?s ?p ?o { ?s ?p ?o } LIMIT 1"

        for i in range(max_retries):
            try:
                response = requests.post(url, headers=headers, data=test_query)
                if response.status_code == 200:
                    return (200, "Server ready!")
            except requests.exceptions.RequestException as e:
                pass
            time.sleep(retry_interval)

        return (500, "Server failed to start within expected time")

    def stop_server(self):
        """
        Stops the SPARQL server.

        Raises:
            subprocess.CalledProcessError: If an error occurs while stopping the server.
        """
        try:
            subprocess.check_call(f"pkill -f '{self.path_to_binaries}/ServerMain -i [^ ]*TestSuite'", shell=True)
        except subprocess.CalledProcessError as e:
            print(f"Error stopping server: {e}")

    def query(self, query, result_format):
        """
        Executes a SPARQL query against the server and retrieves the results.

        Parameters:
            query (str): The SPARQL query to be executed.
            result_format (str): Type of the result.

        Returns:
            tuple: A tuple containing the HTTP status code and the query result.

        Raises:
            requests.exceptions.RequestException: If an error occurs during query execution.
        """
        content_type = "application/sparql-results+json"
        if result_format == "csv":
            content_type = "text/csv"
        elif result_format == "tsv":
            content_type = "text/tab-separated-values"
        elif result_format == "srx":
            content_type = "application/sparql-results+xml"

        url = "http://mint-work:7001"
        headers = {"Accept": content_type, "Content-type": "application/sparql-query; charset=utf-8"}

        try:
            response = requests.post(url, headers=headers, data=query.encode("utf-8"))
            return (response.status_code, response.text)
        except requests.exceptions.RequestException as e:
            return (500, f"Query execution error: {str(e)}")

    def element_to_string(self, element: ET.Element, escaped_xml: str, label: str):
        """
        This function takes an element turns in into a string and if the string is part of the escaped_xml string it will be enclosed with a HTML label

        Parameters:
            original_xml (str): The original XML string to be processed.
            remaining_tree (ET.ElementTree): An ElementTree object representing the XML elements to be highlighted.
            red_tree: ET.ElementTree (ET.ElementTree): An ElemenTree object representing the XML elements to RED otherwise yellow.

        Returns:
            str: An HTML-escaped XML string with specific elements highlighted.
        """      
        element_str = ET.tostring(element).decode("utf8").replace(" />", "/>")
        element_str = element_str.replace("ns0:", "")

        escaped_element_str = escape(element_str)
        if escaped_element_str in escaped_xml:
            return escaped_xml.replace(escaped_element_str, f'</label><label class="{label}">{escaped_element_str}</label><label class="normal">')
        else:
            return escaped_xml

    def generate_highlighted_string_xml(self, original_xml: str, remaining_tree: ET.ElementTree, red_tree: ET.ElementTree) -> str:
        """
        This method takes an XML string and an ElementTree object representing a subset of the XML. 
        It escapes the XML string for HTML display and then highlights the elements from the 
        ElementTree within the escaped XML string. Elements to be highlighted are wrapped in a 
        <label> tag.

        Parameters:
            original_xml (str): The original XML string to be processed.
            remaining_tree (ET.ElementTree): An ElementTree object representing the XML elements to be highlighted.
            red_tree: ET.ElementTree (ET.ElementTree): An ElemenTree object representing the XML elements to RED otherwise yellow.

        Returns:
            str: An HTML-escaped XML string with specific elements highlighted.
        """
        escaped_xml = escape(original_xml)

        for element in remaining_tree.getroot().findall('.//head'):
            escaped_xml = self.element_to_string(element, escaped_xml, "red")

        for element in remaining_tree.getroot().findall('.//result'):
            label = "yellow"
            for elem in red_tree.getroot().findall('.//result'):
                if (elem.tag == element.tag and 
                    elem.attrib == element.attrib and 
                    elem.text == element.text):
                    label = "red"
            escaped_xml = self.element_to_string(element, escaped_xml, label)

        return escaped_xml

    def strip_namespace(self, tree: ET.ElementTree) -> ET.ElementTree:
        """
        Removes the namespace from the tags in an XML ElementTree.

        Parameters:
            tree (ET.ElementTree): An XML ElementTree with namespace in the tags.

        Returns:
            ET.ElementTree: The modified XML ElementTree with namespace removed from tags.
        """
        for elem in tree.iter():
            elem.tag = elem.tag.partition("}")[-1]
        return tree

    def generate_html_for_xml(self, xml1: str, xml2: str, remaining_tree1: ET.ElementTree, remaining_tree2: ET.ElementTree, red_tree1: ET.ElementTree, red_tree2: ET.ElementTree) -> tuple:
        """
        Generates HTML representations for two XML strings with specific elements highlighted.

        Parameters:
            xml1 (str): The first XML string to be processed.
            xml2 (str): The second XML string to be processed.
            remaining_tree1 (ET.ElementTree): representing the XML elements to be highlighted for the first XML string.
            remaining_tree2 (ET.ElementTree): representing the XML elements to be highlighted for the second XML string.

        Returns:
            tuple: A tuple containing two HTML-escaped and highlighted XML strings.
        """
        highlighted_xml1 = f'<label class="normal">{self.generate_highlighted_string_xml(xml1, self.strip_namespace(remaining_tree1), self.strip_namespace(red_tree1))}</label>'
        highlighted_xml2 = f'<label class="normal">{self.generate_highlighted_string_xml(xml2, self.strip_namespace(remaining_tree2), self.strip_namespace(red_tree2))}</label>'

        return highlighted_xml1, highlighted_xml2

    def xml_elements_equal(self, element1: ET.Element, element2: ET.Element, compare_with_intended_behaviour: bool) -> bool:
        """
        Compares two XML elements for equality in tags, attributes and text.
        Parameters:
            e1 (ET.Element): The first XML element
            element2 (ET.Element): The second XML element
            compare_with_intended_behaviour (bool): Bool to determine whether to use intended behaviour aliases in comparison.

        Returns:
            bool: True if elements are considered equal and if not False.
        """
        is_number = False
        if element1.tag != element2.tag:
            if (self.alias.get(element1.tag) != element2.tag and self.alias.get(element2.tag) != element1.tag) or not compare_with_intended_behaviour: 
                return False

        if element1.attrib != element2.attrib: 
            if isinstance(element1.attrib, dict) != isinstance(element2.attrib, dict): return False
            if not isinstance(element1.attrib, dict) and (self.alias.get(element1.attrib) != element2.attrib and self.alias.get(element2.attrib) != element1.attrib) or not compare_with_intended_behaviour: return False
            if isinstance(element1.attrib, dict) and (self.alias.get(element1.attrib.get("datatype")) != element2.get("datatype") and self.alias.get(element2.attrib.get("datatype")) != element1.attrib.get("datatype")) or not compare_with_intended_behaviour: return False
        
        if (element1.attrib.get("datatype") in self.number_types) != (element2.attrib.get("datatype") in self.number_types): return False

        if element1.attrib.get("datatype") in self.number_types and element2.attrib.get("datatype") in self.number_types:
            is_number = True
    
        if element1.text != element2.text:
            if element1.tag == "{http://www.w3.org/2005/sparql-results#}bnode":
                if element1.text not in self.map_bnodes and element2.text not in self.map_bnodes:
                    self.map_bnodes[element1.text] = element2.text
                    self.map_bnodes[element2.text] = element1.text
                    return all(self.xml_elements_equal(c1, c2, compare_with_intended_behaviour) for c1, c2 in zip(element1, element2))
                elif self.map_bnodes.get(element1.text) == element2.text and self.map_bnodes.get(element2.text) == element1.text:
                    return all(self.xml_elements_equal(c1, c2, compare_with_intended_behaviour) for c1, c2 in zip(element1, element2))
                return False
            if (element1.text is None and element2.text.strip() == "") or (element2.text is None and element1.text.strip() == ""):
                return all(self.xml_elements_equal(c1, c2, compare_with_intended_behaviour) for c1, c2 in zip(element1, element2))
            if element1.text is None or element2.text is None:  return False
            if element1.text.strip() == element2.text.strip(): return all(self.xml_elements_equal(c1, c2, compare_with_intended_behaviour) for c1, c2 in zip(element1, element2))
            if is_number:
                if float(element1.text) == float(element2.text): return all(self.xml_elements_equal(c1, c2, compare_with_intended_behaviour) for c1, c2 in zip(element1, element2))
            if (self.alias.get(element1.text) != element2.text and self.alias.get(element2.text) != element1.text) or not compare_with_intended_behaviour: return False
        return all(self.xml_elements_equal(c1, c2, compare_with_intended_behaviour) for c1, c2 in zip(element1, element2))

    def xml_remove_equal_elements(self, parent1: ET.Element, parent2: ET.Element, use_config: bool):
        """
        Compares and removes equal child elements from two parent XML elements.

        This method iterates over the children of two given parent XML elements and removes
        matching children from both parents.

        Parameters:
            parent1 (ET.Element): The first parent XML element.
            parent2 (ET.Element): The second parent XML element.
            use_config (bool): Configuration Bool to control comparison behavior.
        """
        for child1 in list(parent1):
            for child2 in list(parent2):
                if self.xml_elements_equal(child1, child2, use_config):
                    parent1.remove(child1)
                    parent2.remove(child2)
                    break

    def compare_xml(self, test: tuple, expected_xml: str, query_xml: str) -> tuple:
        """
        Compares two XML documents, identifies differences and generates HTML representations.

        This method compares two XML documents and identifies differences.
        It removes equal elements in both documents and generates HTML representations highlighting the remaining differences.

        Parameters:
            test (tuple): The test details.
            expected_xml (str): The expected XML content as a string.
            query_xml (str): The query XML content as a string.

        Returns:
            tuple: A tuple containing the status and error type.
        """
        self.map_bnodes = {}
        status = "Failed"
        error_type = "RESULTS NOT THE SAME"
        expected_tree = ET.ElementTree(ET.fromstring(expected_xml))
        query_tree = ET.ElementTree(ET.fromstring(query_xml))

        # Compare and remove equal elements in <head>
        head1 = expected_tree.find(".//{http://www.w3.org/2005/sparql-results#}head")
        head2 = query_tree.find(".//{http://www.w3.org/2005/sparql-results#}head")
        if head1 is not None and head2 is not None:
            self.xml_remove_equal_elements(head1, head2, False)

        # Compare and remove equal <result> elements in <results>
        results1 = expected_tree.find(".//{http://www.w3.org/2005/sparql-results#}results")
        results2 = query_tree.find(".//{http://www.w3.org/2005/sparql-results#}results")
        
        if results1 is not None and results2 is not None:
            self.xml_remove_equal_elements(results1, results2, False)

        # Copy expected_tree
        expected_tree_string = ET.tostring(expected_tree.getroot())
        copied_expected_tree = ET.ElementTree(ET.fromstring(expected_tree_string))

        # Copy query_tree
        query_tree_string = ET.tostring(query_tree.getroot())
        copied_query_tree = ET.ElementTree(ET.fromstring(query_tree_string))

        if len(list(results1)) == 0 and len(list(results2)) == 0 and len(list(head1)) == 0 and len(list(head2)):
            status = "Passed"
            error_type = ""
        else:
            if results1 is not None and results2 is not None:
                self.xml_remove_equal_elements(results1, results2, True)
        
            if len(list(results1)) == 0 and len(list(results1)) == 0:
                status = "Failed: Intended behaviour"
                error_type = "Known, intended behaviour that does not comply with SPARQL standard"
        
        expected_string, query_string = self.generate_html_for_xml(expected_xml, query_xml,copied_expected_tree, copied_query_tree, expected_tree, query_tree)
        test_name = test[2]
        self.test_data[test_name].update({"expectedHtml": expected_string, "gotHtml": query_string})

        return status, error_type

    def handle_bindings(self, indent: int, level: int, bindings: list, remaining_bindings: list, mark_red: list) -> str:
        """
        Formats the "bindings" list with HTML labels as needed for highlighting.

        This method iterates over a list of bindings and applies HTML labels to those
        that match any in the reference bindings list. The method handles indentation
        and formatting to create a readable HTML-formatted string.

        Parameters:
            indent (int): Number of spaces used for indentation.
            level (int): Current nesting level for correct indentation.
            bindings (list): List of binding items to format.
            remaining_bindings (list): List of binding items used for comparison.
            mark_red (list): List containing the elements that must be highlighted red.

        Returns:
            str: An HTML-formatted string representing the bindings list with highlighted items.
        """
        parts = ["["]
        for i, binding in enumerate(bindings):
            if i > 0:
                parts.append(", ")
            parts.append("\n" + " " * (indent * (level + 1)))
            
            # Apply label if the binding matches any in the reference bindings
            if binding in remaining_bindings:
                if binding in mark_red:
                    label = '</label><label class="red">'
                else:
                    label = '</label><label class="yellow">'
                end_label = '</label><label class="normal">'
            else:
                label = ""
                end_label = ""
            parts.append(f"{label}{self.json_to_string(binding, {}, level + 1)}{end_label}")
        parts.append("\n" + " " * (indent * level) + "]")
        return "".join(parts)

    def json_dict(self, indent: int, level: int, json_dict: dict, remaining_dict: dict, mark_red: list) -> str:
        """
        Formats a dictionary with HTML labels as needed for highlighting.

        Iterates through the dictionary and formats each key-value pair. Special handling is
        applied for lists under specific keys "vars" and "bindings". The method manages
        indentation and applies HTML labels for highlighting as needed.

        Parameters:
            indent (int): Number of spaces used for indentation.
            level (int): Current nesting level for correct indentation.
            json_dict (dict): Dictionary to format.
            remaining_dict (dict): Dictionary used for comparison to determine highlighting.
            mark_red (list): List containing the elements that must be highlighted red.

        Returns:
            str: An HTML-formatted string representing the dictionary with highlighted elements.
        """
        parts = ["{"]
        for i, (key, value) in enumerate(json_dict.items()):
            if i > 0:
                parts.append(", ")
            parts.append("\n" + " " * (indent * (level + 1)))

            if isinstance(value, list) and key == "vars":
                # Special handling for "vars" in "head"
                parts.append(f"\"{key}\": {self.json_to_string(value, remaining_dict.get(key, []),mark_red, level + 1)}")
            elif isinstance(value, list) and key == "bindings":
                # Special handling for "bindings" in "results"
                formatted_bindings = self.handle_bindings(indent, level, value, remaining_dict.get(key, []), mark_red)
                parts.append(f"\"{key}\": {formatted_bindings}")
            else:
                parts.append(f"\"{key}\": {self.json_to_string(value, remaining_dict.get(key, {}), mark_red, level + 1)}")
        
        parts.append("\n" + " " * (indent * level) + "}")
        return "".join(parts)

    def json_list(self, indent: int, level: int, json_list: list, remaining_list: list, mark_red: list) -> str:
        """
        Formats a list with HTML labels as needed for highlighting.

        Iterates through the list and applies HTML labels to items that match
        any in the reference list. Manages indentation for a readable format.

        Parameters:
            indent (int): Number of spaces used for indentation.
            level (int): Current nesting level for correct indentation.
            json_list (list): List of items to format.
            remaining_list (list): List used for comparison to determine highlighting.
            mark_red (list): List containing the elements that must be highlighted red.

        Returns:
            str: An HTML-formatted string representing the list with highlighted elements.
        """
        parts = ["["]
        for i, item in enumerate(json_list):
            if i > 0:
                parts.append(", ")
            parts.append("\n" + " " * (indent * (level + 1)))
            # Apply label if the item is in the reference list
            if item in remaining_list:
                if item in mark_red:
                    label = '</label><label class="red">'
                else:
                    label = '</label><label class="yellow>"'
                end_label = '</label><label class="normal">'
            else:
                label = ""
                end_label = ""
            parts.append(f"{label}\"{item}\"{end_label}")
        parts.append("\n" + " " * (indent * level) + "]")
        return "".join(parts)

    def json_to_string(self, json_obj, remaining_json, mark_red: list, level=0) -> str:
        """
        Converts a JSON object to a readable string and highlights elements found in the reference JSON with <"></">.

        Parameters:
        json_obj (dict or list): The JSON object to be converted.
        remaining_json (dict or list): SON object to check for matching elements.
        mark_red (list): List containing the elements that must be highlighted red.
        level (int): Current recursion level to calculate indentation.

        Returns:
        str: A readable string representation of the JSON object with highlighted elements.
        """
        indent=4
        if isinstance(json_obj, dict):
            return self.json_dict(indent, level, json_obj, remaining_json, mark_red)
        elif isinstance(json_obj, list):
            return self.json_list(indent, level, json_obj, remaining_json, mark_red)
        elif isinstance(json_obj, str):
            return f"\"{json_obj}\""
        else:
            return str(json_obj)

    def generate_highlighted_string_json(self, json_obj: dict, remaining_json: dict, mark_red: list) -> str:
        """
        Generates an HTML-formatted and highlighted string representation of a JSON object.

        Parameters:
            json_obj: The JSON object to be formatted and highlighted.
            remaining_json: The JSON object used as a reference for highlighting elements in the json_obj.
            mark_red (list): List containing the elements that must be highlighted red.

        Returns:
            str: An HTML string representing the formatted and highlighted JSON object.
        """
        return f'<label class="normal">{self.json_to_string(json_obj, remaining_json, mark_red)}</label>'

    def json_elements_equal(self, element1: dict, element2: dict, compare_with_intended_behaviour: bool) -> bool:
        """
        Compares two JSON elements for equality.

        This method compares two JSON elements for equality. It checks for matching
        keys and compares their values. It also accounts for datatype differences by comparing numerical values. 
        The comparison can include intended behavior based on the compare_with_intended_behaviour Bool.

        Parameters:
            element1 (dict): The first JSON element to compare.
            element2 (dict): The second JSON element to compare.
            compare_with_intended_behaviour (bool): Bool to determine whether to use intended behavior aliases in comparison.

        Returns:
            bool: True if considered equal otherwise False.
        """
        if set(element1.keys()) != set(element2.keys()):
            return False
        for key in element1:
            field1 = element1[key]
            field2 = element2[key]

            if isinstance(field1, dict) and isinstance(field2, dict):
                for sub_key in set(field1.keys()) | set(field2.keys()):
                    if field1.get(sub_key) != field2.get(sub_key):
                        if str(field1.get("type")) == "bnode" and str(field2.get("type")) == "bnode" and str(sub_key) == "value":
                            if field1.get("value") not in self.map_bnodes and field2.get("value") not in self.map_bnodes:
                                self.map_bnodes[field1.get("value")] = field2.get("value")
                                self.map_bnodes[field2.get("value")] = field1.get("value")
                                continue
                            if self.map_bnodes.get(field1.get("value")) == field2.get("value") and self.map_bnodes.get(field2.get("value")) == field1.get("value"):
                                continue
                        if str(field1.get("datatype")) in self.number_types and str(field2.get("datatype")) in self.number_types and str(sub_key) == "value":
                            if float(field1.get(sub_key)) == float(field2.get(sub_key)):
                                continue
                        if ((str(self.alias.get(str(field1.get(sub_key)))) == str(field2.get(sub_key))) or (str(self.alias.get(str(field2.get(sub_key)))) == str(field1.get(sub_key)))) and compare_with_intended_behaviour:
                            continue
                        return False
            else:
                if field1 != field2:
                    return False
        return True

    def compare_json(self, test: tuple, expected_json: str, query_json: str) -> tuple:
        """
        Compares two JSON objects and identifies differences in their "head" and "results" sections.

        This method parses two JSON strings representing expected and query results. It compares
        these JSON objects, particularly focusing on the "head" and "results" sections.
        Differences are highlighted, and a status of comparison along with any error type is returned.

        Parameters:
            test (tuple): The test details.
            expected_json (str): The expected JSON content as a string.
            query_json (str): The query JSON content as a string.

        Returns:
            tuple: A tuple containing the status and error type.
        """
        self.map_bnodes = {}
        status = "Failed"
        error_type = "RESULTS NOT THE SAME"
        expected = json.loads(expected_json)
        query = json.loads(query_json)

        vars1 = expected["head"]["vars"]
        vars2 = query["head"]["vars"]
        
        # Compare and remove similar parts in "head" section
        unique_vars1 = [v for v in vars1 if v not in vars2]
        unique_vars2 = [v for v in vars2 if v not in vars1]
        
        expected["head"]["vars"] = unique_vars1
        query["head"]["vars"] = unique_vars2
        
        # Compare and remove similar parts in "bindings" section using the custom comparison function
        bindings1 = expected["results"]["bindings"]
        bindings2 = query["results"]["bindings"]

        unique_bindings1 = [b1 for b1 in bindings1 if not any(self.json_elements_equal(b1, b2, compare_with_intended_behaviour=False) for b2 in bindings2)]
        unique_bindings2 = [b2 for b2 in bindings2 if not any(self.json_elements_equal(b2, b1, compare_with_intended_behaviour=False) for b1 in bindings1)]

        expected["results"]["bindings"] = unique_bindings1
        query["results"]["bindings"] = unique_bindings2

        if len(expected["results"]["bindings"]) == 0 and len(query["results"]["bindings"]) == 0 and len(expected["head"]["vars"]) == 0 and len(query["head"]["vars"]) == 0:
            status = "Passed"
            error_type = ""
        else:
            unique_bindings1 = [b1 for b1 in bindings1 if not any(self.json_elements_equal(b1, b2, compare_with_intended_behaviour=True) for b2 in bindings2)]
            unique_bindings2 = [b2 for b2 in bindings2 if not any(self.json_elements_equal(b2, b1, compare_with_intended_behaviour=True) for b1 in bindings1)]
            if len(unique_bindings1) == 0 and len(unique_bindings2) == 0:
                status = "Failed: Intended behavior"
                error_type = "Known, intended behaviour that does not comply with SPARQL standard"
        expected_string = self.generate_highlighted_string_json(json.loads(expected_json), expected, unique_bindings1)
        query_string = self.generate_highlighted_string_json(json.loads(query_json), query, unique_bindings2)
        test_name = test[2]
        self.test_data[test_name].update({"expectedHtml": expected_string, "gotHtml": query_string})
        
        return status, error_type

    def compare_values(self, value1: str, value2: str, is_number: bool, use_config: bool) -> bool:
        """
        Compares two values for equality accounting for numeric differences and aliases.

        Parameters:
            value1 (str): The first value to compare.
            value2 (str): The second value to compare.
            is_number (bool): Indicates if the values should be treated as numbers.
            use_config (bool): Flag to use configuration for additional comparison logic.

        Returns:
            bool: True if the values are considered equal.
        """
        if value1 is None or value2 is None:
            return False
        # Blank nodes
        if len(value1) > 1 and len(value2) > 1 and value1[0] == "_" and value2[0] == "_":
            if value1 not in self.map_bnodes and value2 not in self.map_bnodes:
                self.map_bnodes[value1] = value2
                self.map_bnodes[value2] = value1
                return True
            if self.map_bnodes.get(value1) == value2 and self.map_bnodes.get(value2) == value1:
                return True
            return False
        # In most cases the values are in the same representation
        if value1 == value2:
            return True
        # Handle exceptions ex. 30000 == 3E4
        if value1[0].isnumeric() and value2[0].isnumeric() and is_number:
            if float(value1) == float(value2):
                return True
        else:  # Handle exceptions integer = int
            if value1 in self.alias and self.alias[value1] == value2 and use_config:
                return True
        return False

    def compare_rows(self, row1: list, row2: list, use_config:bool) -> bool:
        """
        Compares two rows for equality.

        Parameters:
            row1 (list): The first row to compare.
            row2 (list): The second row to compare.
            use_config (bool): Flag to use configuration for additional comparison logic.

        Returns:
            bool: True if the rows are considered equal otherwise False
        """
        if len(row1) != len(row2):
            return False

        for element1, element2 in zip(row1, row2):
            if not self.compare_values(element1.split("^")[0], element2.split("^")[0], True, use_config):
                return False
        return True

    def row_to_string(self, row: list, separator: str) -> str:
        """
        Converts a row (list of values) to a string representation separated by a specified delimiter.

        Parameters:
            row (list): The row to be converted to a string.
            separator (str): The separator used to separate the values in the row "," or "\t"

        Returns:
            str: A string representation of the row.
        """
        result = ""
        index = 0
        row_length = len(row) - 1
        for element in row:
            if index == row_length:
                delimiter = ""
            else:
                delimiter = separator
            result += str(element) + delimiter
            index += 1
        return result

    def generate_highlighted_string_sv(self, array: list, remaining: list, mark_red: list, result_type: str) -> str:
        """
        Generates a string representation of an array, with specific rows highlighted.

        Parameters:
            array (list): The array to be converted to a string.
            remaining (list): The rows to be highlighted.
            result_type (str): The type of result (csv or tsv) to determine the separator.

        Returns:
            str: A string representation of the array with highlighted rows.
        """
        separator = "," if result_type == "csv" else "\t"
        
        result_string = ""
        for row in array:
            if row in remaining:
                if row in mark_red:
                    result_string += '</label><label class="red">'
                else:
                    result_string += '</label><label class="yellow">'
                result_string += escape(self.row_to_string(row, separator))
                result_string += '</label>\n<label class="normal">'
            else:
                result_string += escape(self.row_to_string(row, separator)) + "\n"
        return '<label class="normal">' + result_string + '</label>'

    def compare_array(self, expected_result: list, result: list, result_copy: list, expected_result_copy: list, use_config: bool):
        """
        Compares two arrays and removes equal rows from both arrays.

        Parameters:
            expected_result (list): The expected result array.
            result (list): The actual result array.
            result_copy (list): A copy of the actual result array for modification.
            expected_result_copy (list): A copy of the expected result array for modification.
            use_config (bool): Flag to use configuration for additional comparison logic.
        """
        for row1 in result:
            equal = False
            row2_delete = None
            for row2 in expected_result:
                if self.compare_rows(row1, row2, use_config):
                    equal = True
                    row2_delete = row2
                    break
            if equal:
                result_copy.remove(row1)
                expected_result_copy.remove(row2_delete)

    def convert_csv_tsv_to_array(self, input_string: str, input_type: str):
        """
        Converts a CSV/TSV string to an array of rows.

        Parameters:
            input_string (str): The CSV/TSV formatted string.
            input_type (str): The type of the input ('csv' or 'tsv').

        Returns:
            An array representation of the input string.
        """
        rows = []
        delimiter = "," if input_type == "csv" else "\t"
        with StringIO(input_string) as io:
            reader = csv.reader(io, delimiter=delimiter)
            for row in reader:
                rows.append(row)
        return rows

    def compare_sv(self, test: tuple, expected_string: str, query_result: str, result_format: str):
        """
        Compares CSV/TSV formatted query result with the expected output.

        Parameters:
            test (tuple): Details of the current test.
            expected_string (str): Expected CSV/TSV formatted string.
            query_result (str): Actual CSV/TSV formatted string from the query.
            output_format (str): Format of the output ('csv' or 'tsv').

        Returns:
            A tuple of test status and error message.
        """
        self.map_bnodes = {}
        status = "Failed"
        error_type = "RESULTS NOT THE SAME"

        expected_array = self.convert_csv_tsv_to_array(expected_string, result_format)
        actual_array = self.convert_csv_tsv_to_array(query_result, result_format)
        actual_array_copy = actual_array.copy()  
        expected_array_copy = expected_array.copy()
        actual_array_mark_red = []
        expected_array_mark_red = []

        self.compare_array(expected_array, actual_array, actual_array_copy, expected_array_copy, use_config=False)

        if len(actual_array_copy) == 0 and len(expected_array_copy) == 0:
            status = "Passed"
            error_type = ""
        else:
            actual_array_mark_red = actual_array_copy.copy()
            expected_array_mark_red = expected_array_copy.copy()
            self.compare_array(expected_array_copy, actual_array_copy, actual_array_mark_red, expected_array_mark_red, use_config=True)
            if len(actual_array_mark_red) == 0 and len(expected_array_mark_red) == 0:
                status = "Failed: Intended behavior" 
                error_type = "Known, intended behaviour that does not comply with SPARQL standard"
        
        expected_html = self.generate_highlighted_string_sv(expected_array, expected_array_copy, expected_array_mark_red, result_format)
        actual_html = self.generate_highlighted_string_sv(actual_array, actual_array_copy, actual_array_mark_red, result_format)
        test_name = test[2]
        self.test_data[test_name].update({"expectedHtml": expected_html, "gotHtml": actual_html})

        return status, error_type

    def evaluate_query(self, expected_string: str, query_result: str, test: tuple, result_format: str) -> tuple:
        """
        Evaluates a query result based on the expected output and the format.

        Parameters:
            test (tuple): Information about the test being run.
            expected_output (str): The expected output of the query.
            query_result (str): The actual output received from the query.
            result_format (str): The format of the query output ("csv", "tsv", "srx", "srj").

        Returns:
            A tuple containing the status of the test and the type of error.
        """
        status = "Failed"
        errorType = "RESULTS NOT THE SAME"
        if result_format == "srx":
            status, errorType = self.compare_xml(test, expected_string, query_result)
        elif result_format == "srj":
            status, errorType = self.compare_json(test, expected_string, query_result)
        elif (result_format == "csv" or result_format == "tsv"):
            status, errorType = self.compare_sv(test, expected_string, query_result, result_format)
        return status, errorType

    def update_test_status(self, test_name: str, status: str, error_type: str):
        """
        Updates the status of a test in the test data.

        Parameters:
            test_name (str): The name of the test.
            status (str): The status of the test.
            error_type (str): The error message associated with the test.
        """
        self.test_data[test_name].update({"status": status, "errorType": error_type})
        if status == "Passed":
            self.passed += 1
        elif status == "Failed":
            self.failed += 1
        else:
            self.passed_failed += 1

    def process_test(self, test: tuple, query_result: str, expected_string: str, type_name: str, result_format: str):
        """
        Processes an individual test evaluating its result and updating its status.

        Parameters:
            test (tuple): Details of the test to process.
            query_result (str): The output received from the query execution.
            expected_string (str): The expected output of the query.
            type_name (str): The type of the test.
            result_format (str): The format of the query output.
        """
        status, error_type = "Failed", ""
        if query_result[0] == 200:
            if type_name == "QueryEvaluationTest" or "CSVResultFormatTest":
                status, error_type = self.evaluate_query(expected_string, query_result[1], test, result_format)
        else:
            if "exception" in query_result[1]:
                error_type = "QUERY EXCEPTION"
                self.test_data[test[2]].update({"queryLog": query_result[1]})
            elif "HTTP Request" in query_result[1]:
                error_type = "REQUEST ERROR"
            else:    
                error_type = "Undefined error"

        if type_name == "PositiveSyntaxTest11":
            if error_type != "":
                status = "Failed"
            else:
                status = "Passed"
                error_type = ""
        if type_name == "NegativeSyntaxTest11":
            if error_type == "QUERY EXCEPTION":
                status = "Passed"
                error_type = ""
            else:
                status = "Failed"
                error_type = "EXPECTED: QUERY EXCEPTION ERROR"
        self.update_test_status(test[2], status, error_type)

    def prepare_test(self, test: tuple):
        """
        Prepares the execution of a test by setting up the necessary environment and data.

        Parameters:
            test: Details of the test to be executed.
        """
        type_name = self.test_data[test[2]]["typeName"]
        expected_string = self.test_data[test[2]]["resultFile"]
        query_string = self.test_data[test[2]]["queryFile"].replace("\n", " ")
        self.test_data[test[2]]["querySent"] = query_string
        result_format = test[1][test[1].rfind(".") + 1:]

        query_result = self.query(query_string, result_format)

        self.process_test(test, query_result, expected_string, type_name, result_format)


    def log_for_all_tests(self, graph: str, error_type: str, index_log: str, server_log: str, failed: bool):
        """
        Logs information for all tests in a given graph.

        Parameters:
            graph (str): The graph.
            error_type (str): Type of error encountered.
            index_log (str): Log information from the indexing process.
            server_log (str): Log information from the server.
            failed (bool): Boolean indicating if the test failed.
        """
        for test in self.tests_of_graph[graph]:
            test_name = test[2]
            if failed:
                self.update_test_status(test_name, "Failed", error_type)
            self.test_data[test_name].update({"indexLog": self.remove_date_time_parts(index_log), "serverLog": server_log})

    def start_graph_server(self, graph):
        """
        Starts the server for a specific graph.

        Parameters:
            graph: The graph for which the server is to be started.

        Returns:
            True if the server started successfully, False otherwise.
        """
        server_result = self.start_server()
        if server_result[0] != 200:
            self.log_for_all_tests(graph, "SERVER ERROR", "", server_result[1], True)
            return False
        return True

    def remove_date_time_parts(self, index_log: str) -> str:
        """
        Remove date and time from index log.
        ex. 2023-12-20 14:02:33.089	- INFO:  You specified the input format: TTL
        to: INFO:  You specified the input format: TTL

        Parameters:
            index_log (str): The index log.

        Returns:
            The index log without time and date as a string.
        """
        pattern = r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3}\s*-'
        return re.sub(pattern, '', index_log)

    def index_graph(self, graph: str, graph_path: str):
        """
        Indexes a given graph.

        Parameters:
            graph: The graph to index.
            graph_path: The file path of the graph.

        Returns:
            True if indexing is successful, False otherwise.
        """
        index_log = self.index(graph_path)

        if "Index build completed" not in index_log:
            self.log_for_all_tests(graph, "INDEX BUILD ERROR", self.remove_date_time_parts(index_log), "", True)
            return False
        self.log_for_all_tests(graph, "", index_log, "", False)
        return True

    def prepare_test_environment(self, graph: str, graph_path: str):
        """
        Prepares the test environment for a given graph.

        Parameters:
            graph: The graph to be tested.
            graph_path: The path to the graph file.

        Returns:
            True if the environment is successfully prepared, False otherwise.
        """
        if not self.index_graph(graph, graph_path):
            return False
        if not self.start_graph_server(graph):
            return False
        return True

    def run_query_tests(self):
        """
        Executes query tests for each graph in the test suite.
        """
        self.remove_index()
        for graph in self.tests_of_graph:
            graph_path = os.path.join(self.path_to_test_suite, graph)
            print(f"Running tests for graph: {graph_path}")

            if not self.prepare_test_environment(graph, graph_path):
                continue

            for test in self.tests_of_graph[graph]:
                self.prepare_test(test)

            self.stop_server()
            self.remove_index()

    def run(self):
            """
            Main method to run all query tests.
            """
            self.run_query_tests()

    def extract_tests(self, output_csv_path: str):
        """
        Extracts tests from a set of directories and compiles results into a CSV file.

        Parameters:
            output_csv_path: Path to the output CSV file.
        """
        dir_paths = self.read_file("directories.txt").split("\n")
        queries = ["Query.rq", "Syntax.rq", "Protocol.rq", "Update.rq", "Format.rq"]
        csv_rows = []

        for path in dir_paths:
            print("Extracting tests from: " + path)
            self.remove_index()
            self.index(self.path_to_test_suite + path + "/manifest.ttl")
            self.start_server()
            for query in queries:
                query_result = self.query(self.read_file(query), "csv")
                if query_result[0] == 200:
                    csv_content = query_result[1]

                    csv_reader = csv.reader(csv_content.splitlines())
                    next(csv_reader)
                    for row in csv_reader:
                        csv_rows.append(row)
            self.stop_server()
        with open(output_csv_path, "w", newline="") as csvfile:
            csv_writer = csv.writer(csvfile)
            csv_writer.writerows(csv_rows)

    def generate_json_file(self):
        """
        Generates a JSON file with the test results.
        """
        os.makedirs("./results", exist_ok=True)
        file_path = f"./results/{self.name}.json"
        data = {}
        data[self.name] = self.test_data
        data[self.name]["info"] = {"name": "info",
                                   "passed": self.passed,
                                   "tests": self.tests,
                                   "failed": self.failed,
                                   "passedFailed": self.passed_failed,
                                   "notTested": (self.tests - self.passed - self.failed - self.passed_failed)}
        with open(file_path, "w") as file:
            json.dump(data, file, indent=4)

def main():
    args = sys.argv[1:]
    if len(args) != 3:
        print(f"Usage to extract tests: python3 {sys.argv[0]} <path to binaries> <file> extract\n Usage to extract tests: python3 {sys.argv[0]} <path to binaries> <file> <name of the run>)")
        sys.exit()
    test_suite = TestSuite(args[0], args[2])
    test_suite.initialize_config()
    if args[2] == "extract":
        print("GET TESTS!")
        test_suite.extract_tests(args[1])
    else:
        print("RUN TESTS!")
        test_suite.initialize_tests(args[1])
        test_suite.run()
        test_suite.generate_json_file()
    print("DONE!")

if __name__ == "__main__":
    main()