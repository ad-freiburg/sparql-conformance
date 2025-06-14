from typing import Optional, List, Union, Dict, Any
from backend.util import local_name, read_file, escape
import os
import json

# Test status constants
FAILED = 'Failed'
PASSED = 'Passed'
INTENDED = 'Failed: Intended'
QUERY_EXCEPTION = 'QUERY EXCEPTION'
REQUEST_ERROR = 'REQUEST ERROR'
UNDEFINED_ERROR = 'UNDEFINED ERROR'
INDEX_BUILD_ERROR = 'INDEX BUILD ERROR'
SERVER_ERROR = 'SERVER ERROR'
NOT_TESTED = 'NOT TESTED'
RESULTS_NOT_THE_SAME = 'RESULTS NOT THE SAME'
INTENDED_MSG = 'Known, intended behaviour that does not comply with SPARQL standard'
EXPECTED_EXCEPTION = 'EXPECTED: QUERY EXCEPTION ERROR'
FORMAT_ERROR = 'QUERY RESULT FORMAT ERROR'
NOT_SUPPORTED = 'CONTENT TYPE NOT SUPPORTED'


class Config:
    """Configuration class for SPARQL test suite execution."""

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize configuration with settings from dictionary.
        """
        self.HOST = config.get('HOST')
        self.GRAPHSTORE = config.get('GRAPHSTORE')
        self.NEWPATH = config.get('NEWPATH')
        self.alias = config.get('alias')
        self.number_types = config.get('number_types')
        self.path_to_test_suite = os.path.abspath(config.get('path_to_testsuite'))
        self.path_to_binaries = os.path.abspath(config.get('path_to_binaries'))
        self.queries = config.get('queries')
        self.command_index = config.get('command_index')
        self.command_start_server = config.get('command_start_server')
        self.command_stop_server = config.get('command_stop_server')
        self.command_remove_index = config.get('command_remove_index')
        self.server_address = config.get('server_address')
        self.port = config.get('port')
        self.directories = config.get('directories')

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary format."""
        return {
            'alias': self.alias,
            'number_types': self.number_types,
            'queries': self.queries,
            'directories': self.directories,
            'HOST': self.HOST,
            'GRAPHSTORE': self.GRAPHSTORE,
            'NEWPATH': self.NEWPATH
        }


def process_graph_data(graph_data: Union[None, str, Dict, List], target_dict: Dict[str, str]) -> None:
    """
    Process graph data and store results in the target dictionary.
    Result: {'label': 'graph', ...}
    """
    if graph_data is None:
        return

    if isinstance(graph_data, str):
        label = graph_data.split('/')[-1]
        target_dict[label] = read_file(graph_data)
        return

    if not isinstance(graph_data, List):
        graph_data = [graph_data]

    for graph_entry in graph_data:
        if isinstance(graph_entry, dict):
            graph_path = graph_entry.get('graph')
            if graph_path:
                label = graph_entry.get('label', graph_path.split('/')[-1])
                target_dict[label] = read_file(graph_path)
        elif isinstance(graph_entry, str):
            label = graph_entry.split('/')[-1]
            target_dict[label] = read_file(graph_entry)


class TestObject:
    """Represents a single SPARQL test case with its configuration and results."""

    def __init__(
            self,
            test: str,
            name: str,
            type_name: str,
            group: str,
            path: str,
            action_node: Optional[Dict[str, Any]],
            result_node: Optional[Dict[str, Any]],
            approval: Optional[str],
            approved_by: Optional[str],
            comment: Optional[str],
            entailment_regime: Optional[str],
            entailment_profile: Optional[str],
            feature: List[str],
            config: Config,
    ):
        """
        Initialize a test object with all its properties.

        Args:
            test: Test URI
            name: Test name
            type_name: Type of the test
            group: Test group identifier
            path: Path to test files
            action_node: Node containing test actions
            result_node: Node containing expected results
            approval: Test approval status
            approved_by: Approver identifier
            comment: Test description/comment
            entailment_regime: SPARQL entailment regime
            entailment_profile: Entailment profile
            feature: List of test features
            config: Test configuration
        """
        self.test = test
        self.name = name
        self.type_name = type_name
        self.group = group
        self.path = path
        self.action_node = action_node
        self.result_node = result_node
        self.approval = approval
        self.approved_by = approved_by
        self.comment = comment
        self.entailment_regime = entailment_regime
        self.entailment_profile = entailment_profile
        self.feature = feature
        self.config = config

        self.status = NOT_TESTED
        self.index_files: Dict[str, str] = {}
        self.result_files: Dict[str, str] = {}

        # Process action node
        if isinstance(action_node, dict):
            self.query = local_name(action_node.get('query', 'no query'))
            self.graph = local_name(action_node.get('data', 'no query'))
            self.query_file = read_file(os.path.join(self.path, self.query))
            self.graph_file = read_file(os.path.join(self.path, self.graph))
            process_graph_data(action_node.get('graphData'), self.index_files)
        else:
            self.query = self.graph = self.query_file = self.graph_file = ''

        # Process result node
        if isinstance(result_node, dict):
            self.result = local_name(result_node.get('data', 'no query'))
            self.result_format = self.result[self.result.rfind('.') + 1:]
            self.result_file = read_file(os.path.join(self.path, self.result))
            process_graph_data(result_node.get('graphData'), self.result_files)
        else:
            self.result = self.result_file = ''

        # Initialize test execution results
        self.error_type = ''
        self.expected_html = ''
        self.got_html = ''
        self.expected_html_red = ''
        self.got_html_red = ''
        self.index_log = ''
        self.server_log = ''
        self.server_status = ''
        self.query_result = ''
        self.query_answer = ''
        self.query_log = ''
        self.query_sent = ''
        self.protocol = ''
        self.protocol_sent = ''
        self.response_extracted = ''
        self.response = ''

    def __repr__(self) -> str:
        """Return string representation of the test object."""
        return f'<TestObject name={self.name}, type={self.type_name}, uri={self.test}>'

    def to_dict(self) -> Dict[str, str]:
        """Convert test object to dictionary format for serialization."""
        self.graph_file = '<b>default:</b> <br> <pre>' + escape(self.graph_file) + '</pre>'
        for name, graph in self.index_files.items():
            self.graph_file += f'<br><b>{name}:</b> <br> <pre>{escape(graph)}</pre>'

        return {
            'test': escape(self.test),
            'typeName': escape(self.type_name),
            'name': escape(self.name),
            'group': escape(self.group),
            'feature': escape(';'.join(self.feature)),
            'comment': escape(self.comment),
            'approval': escape(self.approval),
            'approvedBy': escape(self.approved_by),
            'query': escape(self.query),
            'graph': escape(self.graph),
            'queryFile': escape(self.query_file),
            'graphFile': self.graph_file,
            'resultFile': escape(self.result_file),
            'status': escape(self.status),
            'errorType': escape(self.error_type),
            'expectedHtml': self.expected_html,
            'gotHtml': self.got_html,
            'expectedHtmlRed': self.expected_html_red,
            'gotHtmlRed': self.got_html_red,
            'indexLog': escape(self.index_log),
            'serverLog': escape(self.server_log),
            'serverStatus': escape(self.server_status),
            'queryResult': escape(self.query_result),
            'queryAnswer': escape(self.query_answer),
            'queryLog': escape(self.query_log),
            'querySent': escape(self.query_sent),
            'regime': escape(self.entailment_regime),
            'protocol': escape(self.protocol),
            'protocolSent': escape(self.protocol_sent),
            'responseExtracted': escape(self.response_extracted),
            'response': escape(self.response),
            'config': escape(json.dumps(self.config.to_dict(), indent=4)),
            'indexFiles': escape(json.dumps(self.index_files, indent=4)),
            'resultFiles': escape(json.dumps(self.result_files, indent=4))
        }