import backend.util as util
import os
import json

FAILED = "Failed"
PASSED = "Passed"
INTENDED = "Failed: Intended"
QUERY_EXCEPTION = "QUERY EXCEPTION"
REQUEST_ERROR = "REQUEST ERROR"
UNDEFINED_ERROR = "UNDEFINED ERROR"
INDEX_BUILD_ERROR = "INDEX BUILD ERROR"
SERVER_ERROR = "SERVER ERROR"
NOT_TESTED = "NOT TESTED"
RESULTS_NOT_THE_SAME = "RESULTS NOT THE SAME"
INTENDED_MSG = "Known, intended behaviour that does not comply with SPARQL standard"
EXPECTED_EXCEPTION = "EXPECTED: QUERY EXCEPTION ERROR"
FORMAT_ERROR = "QUERY RESULT FORMAT ERROR"
NOT_SUPPORTED = "CONTENT TYPE NOT SUPPORTED"

# ?type ?name ?query ?result ?data ?test ?feature ?comment ?approval ?approvedBy ?regime ?actionGraphData ?resultGraphData 


class TestObject:
    def __init__(self, row, path_to_test_suite, config):
        self.test = row[5]
        self.type = row[0]
        self.typeName = row[0]
        self.name = row[1]
        self.group = row[-1]
        self.feature = row[6]
        self.comment = row[7]
        self.approval = row[8]
        self.approvedBy = row[9]
        self.regime = row[10]
        self.query = row[2]
        self.graph = row[4]
        self.result = row[3]
        self.namedGraphs = row[11]
        self.resultGraphs = row[12]
        self.queryFile = util.read_file(
            os.path.join(
                path_to_test_suite,
                self.group,
                self.query))
        self.graphFile = util.read_file(
            os.path.join(
                path_to_test_suite,
                self.group,
                self.graph))
        self.resultFile = util.read_file(
            os.path.join(
                path_to_test_suite,
                self.group,
                self.result))
        self.resultFiles = {}
        self.indexFiles = {}
        self.status = NOT_TESTED
        self.errorType = ""
        self.expectedHtml = ""
        self.gotHtml = ""
        self.expectedHtmlRed = ""
        self.gotHtmlRed = ""
        self.indexLog = ""
        self.serverLog = ""
        self.serverStatus = ""
        self.queryResult = ""
        self.queryAnswer = ""
        self.queryLog = ""
        self.querySent = ""
        self.protocol = ""
        self.protocolSent = ""
        self.responseExtracted = ""
        self.response = ""
        self.config = config

        # Handle additional named graphs for the index and the result
        # namedGraphs = "%" means that there are no additional named graphs
        # Format is "graph1%uri1;graph2%uri2;graph3%uri3"
        if self.namedGraphs != "%" and self.namedGraphs != "":
            graphs = self.namedGraphs.split(";")
            for graph in graphs:
                if "%" in graph:
                    graph_name, graph_uri = graph.split("%")
                else:
                    graph_name = graph_uri = graph
                self.indexFiles[graph_uri] = util.read_file(
                    os.path.join(
                        path_to_test_suite,
                        self.group,
                        graph_name))
        
        if self.resultGraphs != "%" and self.namedGraphs != "":
            graphs = self.resultGraphs.split(";")
            for graph in graphs:
                if "%" in graph:
                    graph_name, graph_uri = graph.split("%")
                else:
                    graph_name = graph_uri = graph
                self.resultFiles[graph_uri] = util.read_file(
                    os.path.join(
                        path_to_test_suite,
                        self.group,
                        graph_name))

    def to_dict(self):
        self.graphFile = "<b>default:</b> <br> <pre>" + util.escape(self.graphFile) + "</pre>"
        for name, graph in self.indexFiles.items():
            self.graphFile += f"<br><b>{name}:</b> <br> <pre>{util.escape(graph)}</pre>"
        test_dict = {
            "test": util.escape(self.test),
            "type": util.escape(self.type),
            "typeName": util.escape(self.typeName),
            "name": util.escape(self.name),
            "group": util.escape(self.group),
            "feature": util.escape(self.feature),
            "comment": util.escape(self.comment),
            "approval": util.escape(self.approval),
            "approvedBy": util.escape(self.approvedBy),
            "query": util.escape(self.query),
            "graph": util.escape(self.graph),
            "result": util.escape(self.result),
            "namedGraphs": util.escape(self.namedGraphs),
            "queryFile": util.escape(self.queryFile),
            "graphFile": self.graphFile,
            "resultFile": util.escape(self.resultFile),
            "status": util.escape(self.status),
            "errorType": util.escape(self.errorType),
            "expectedHtml": self.expectedHtml,
            "gotHtml": self.gotHtml,
            "expectedHtmlRed": self.expectedHtmlRed,
            "gotHtmlRed": self.gotHtmlRed,
            "indexLog": util.escape(self.indexLog),
            "serverLog": util.escape(self.serverLog),
            "serverStatus": util.escape(self.serverStatus),
            "queryResult": util.escape(self.queryResult),
            "queryAnswer": util.escape(self.queryAnswer),
            "queryLog": util.escape(self.queryLog),
            "querySent": util.escape(self.querySent),
            "regime": util.escape(self.regime),
            "protocol": util.escape(self.protocol),
            "protocolSent": util.escape(self.protocolSent),
            "responseExtracted": util.escape(self.responseExtracted),
            "response": util.escape(self.response),
            "config": util.escape(json.dumps(self.config.to_dict(), indent=4)),
            "namedGraphs": util.escape(self.namedGraphs),
            "resultGraphs": util.escape(self.resultGraphs),
            "indexFiles": util.escape(json.dumps(self.indexFiles, indent=4)),
            "resultFiles": util.escape(json.dumps(self.resultFiles, indent=4))
        }
        return test_dict


class Config:
    def __init__(self, config):
        self.HOST = config.get("HOST")
        self.GRAPHSTORE = config.get("GRAPHSTORE")
        self.NEWPATH = config.get("NEWPATH")
        self.alias = config.get("alias")
        self.number_types = config.get("number_types")
        self.path_to_test_suite = config.get("path_to_testsuite")
        self.path_to_binaries = config.get("path_to_binaries")
        self.queries = config.get("queries")
        self.command_index = config.get("command_index")
        self.command_start_server = config.get("command_start_server")
        self.command_stop_server = config.get("command_stop_server")
        self.command_remove_index = config.get("command_remove_index")
        self.server_address = config.get("server_address")
        self.port = config.get("port")
        self.directories = config.get("directories")

    def to_dict(self):
        config_dict = {
            "alias": self.alias,
            "number_types": self.number_types,
            "queries": self.queries,
            "directories": self.directories,
            "HOST": self.HOST,
            "GRAPHSTORE": self.GRAPHSTORE,
            "NEWPATH": self.NEWPATH
        }
        return config_dict
