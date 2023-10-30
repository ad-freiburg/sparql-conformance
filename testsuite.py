import os
import sys
import time
import csv
import requests
import json
from io import StringIO
from xml.etree import cElementTree as ElementTree

class TestSuite:
    def __init__(self, path, name):
        self.name = name
        self.pathToBinaries = path
        self.testData = {}
        self.tests = 0
        self.passed = 0
        self.failed = 0
        # QLever changes that are considered the same
        self.alias = {
            "http://www.w3.org/2001/XMLSchema#integer": "http://www.w3.org/2001/XMLSchema#int",
            "http://www.w3.org/2001/XMLSchema#double": "http://www.w3.org/2001/XMLSchema#decimal"}
        self.pathToTestSuite = "./TestSuite/sparql11-test-suite/"
        self.testsOfGraph = {}

    def initializeTests(self, file):
        try:
            with open(file, "r" , newline="") as csvFile:
                csvReader = csv.reader(csvFile)
                # row:
                # test,type,name,feature,comment,approval,approvedBy,query,data,result,regime,action,resultData,request,graphData,graph,resultGraph,label,resultLabel
                for row in csvReader:
                    self.tests += 1
                    # Extract folder the test is located in
                    lastSlashIndex = row[0].rfind("/")
                    secondLastSlashIndex = row[0].rfind("/", 0, lastSlashIndex - 1)
                    pathToTest = row[0][secondLastSlashIndex + 1: lastSlashIndex + 1]
                    # Extract test type
                    lastHashtagIndex = row[1].rfind("#")
                    typeOfTest = row[1][lastHashtagIndex + 1:]

                    if typeOfTest == "QueryEvaluationTest" or typeOfTest == "CSVResultFormatTest" or typeOfTest == "PositiveSyntaxTest11" or typeOfTest == "NegativeSyntaxTest11":
                        if typeOfTest == "PositiveSyntaxTest11" or  typeOfTest == "NegativeSyntaxTest11":
                            if row[8] == "":
                                row[8] = "manifest.ttl"
                            if row[7] == "" and row[11] != "":
                                row[7] = row[11]

                        graphPath = pathToTest + row[8]
                        if graphPath in self.testsOfGraph:
                            self.testsOfGraph[graphPath].append([row[7], row[9], row[2], typeOfTest])
                        else:
                            self.testsOfGraph[graphPath] = [[row[7], row[9], row[2], typeOfTest]]

                    self.testData[row[2]] = {"test": row[0],
                                            "type": row[1],
                                            "typeName" : typeOfTest,
                                            "name": row[2],
                                            "path" : pathToTest,
                                            "feature": row[3],
                                            "comment": row[4],
                                            "approval": row[5],
                                            "approvedBy": row[6],
                                            "query": row[7],
                                            "graph": row[8],
                                            "result": row[9],
                                            "queryFile": self.readFile(self.pathToTestSuite+pathToTest+row[7]),
                                            "graphFile": self.readFile(self.pathToTestSuite+pathToTest+row[8]),
                                            "resultFile": self.readFile(self.pathToTestSuite+pathToTest+row[9]),
                                            "expectedDif": "",
                                            "resultDif": "",
                                            "status": "Not tested",
                                            "errorType": "",
                                            "expected": "",
                                            "got": "",
                                            "indexLog": "",
                                            "serverLog": "",
                                            "serverStatus": "",
                                            "queryLog": "",
                                            "querySent" : "",
                                            "updateGraph" : row[15],
                                            "updateGraphFile" : self.readFile(self.pathToTestSuite+pathToTest+row[15]),
                                            "updateLabel" : row[17],
                                            "updateRequest" : row[13],
                                            "updateRequestFile" : self.readFile(self.pathToTestSuite+pathToTest+row[13]),
                                            "updateResult" : row[16],
                                            "updateResultFile" : self.readFile(self.pathToTestSuite+pathToTest+row[16])}
        except:
            print(file + " does not exist !")

    def readFile(self, file):
        try:
            data = open(file).read()
        except:
            data = ""
        return data

    def index(self, graphPath):
        index = os.popen(
            f"ulimit -Sn 1048576; cat {graphPath} | {self.pathToBinaries}/IndexBuilderMain -F ttl -f - -i TestSuite -s TestSuite.settings.json | tee TestSuite.index-log.txt")
        return index.read()

    def removeIndex(self):
        os.popen("rm -f TestSuite.index.* TestSuite.vocabulary.* TestSuite.prefixes TestSuite.meta-data.json TestSuite.index-log.txt")

    def startSever(self):
        start = os.popen(
            f"{self.pathToBinaries}/ServerMain -i TestSuite -j 8 -p 7001 -m 4 -c 2 -e 1 -k 100 -a 'TestSuite_3139118704' > TestSuite.server-log.txt &")
        # Wait for the server to be ready
        maxRetries = 8  # Maximum number of retries
        retryInterval = 0.25  # Time interval between retries in seconds
        url = "http://mint-work:7001"
        headers = {
            "Content-type": "application/sparql-query"
        }
        testQuery = "SELECT ?s ?p ?o { ?s ?p ?o } LIMIT 1"
        for i in range(maxRetries):
            try:
                response = requests.post(url, headers=headers, data=testQuery)
                if response.status_code == 200:
                    return (200, "")
            except requests.exceptions.RequestException:
                pass 
            time.sleep(retryInterval)

        return (500, response.text)

    def stopServer(self):
        os.popen(
            f"pkill -f '{self.pathToBinaries}/ServerMain -i [^ ]*TestSuite'")

    def query(self, query, resultFile):
        """ 
            Function sends query to qlever-server and returns a tuple consisting of the status code and message
            type specifies the returned format of the http request
        """
        resultFormat = resultFile[resultFile.rfind(".") + 1:]
        if resultFormat == "csv":
            type = "text/csv"
        elif resultFormat == "tsv":
            type = "text/tab-separated-values"
        else:
            type = "application/sparql-results+json"
        url = "http://mint-work:7001"
        headers = {
            "Accept": f"{type}",
            "Content-type": "application/sparql-query"
        }
        response = requests.post(url, headers=headers, data=query)

        return (response.status_code, response.text)

    def compareRows(self, row1, row2):
        if len(row1) != len(row2):
            return False

        for element1, element2 in zip(row1, row2):
            if not self.compareValues(element1.split("^")[0], element2.split("^")[0], True):
                return False
        return True

    def compareValues(self, value1: str, value2: str, isNumber: bool):
        # In most cases the values are in the same representation
        if value1 == value2:
            return True
        # Handle exceptions ex. 30000 == 3E4
        if value1[0].isnumeric() and value2[0].isnumeric() and isNumber:
            if float(value1) == float(value2):
                return True
        else:  # Handle exceptions integer = int
            if value1 in self.alias and self.alias[value1] == value2:
                return True
        return False

    def compareDictionaries(self, dict1, dict2) -> bool:
        dict1Copy = dict(dict1)
        dict2Copy = dict(dict2)
        numberTypes = [
        "http://www.w3.org/2001/XMLSchema#integer",
        "http://www.w3.org/2001/XMLSchema#double",
        "http://www.w3.org/2001/XMLSchema#decimal",
        "http://www.w3.org/2001/XMLSchema#float"
        ]
        isNumber = False
        if "datatype" in dict1:
            if dict1["datatype"] in numberTypes:
                isNumber = True
        if "datatype" in dict2:
            pass
        # Remove the key from the dictionaries if it exists and 
        # has the same value
        for key, value in dict1.items():
            if key in dict2Copy:
                if self.compareValues(value, dict2Copy[key], isNumber):
                    del dict2Copy[key]
                    del dict1Copy[key]
        return not dict1Copy and not dict2Copy

    def compare(self, resultPath, queryResult, test, typeName, resultFormat):
        if typeName == "QueryEvaluationTest" and (resultFormat == "srx" or resultFormat == "srj" ):
            gotDict = self.jsonToDict(queryResult[1])
            if resultFormat == "srx":
                expectedDict = self.xmlToDict(resultPath)
            else:
                expectedDict = self.jsonToDict(self.readFile(resultPath))
            self.testData[test[2]]["expected"] = str(expectedDict)
            self.testData[test[2]]["got"] = str(gotDict)
            return self.compareJSON(gotDict, expectedDict)
        elif (resultFormat == "csv" or resultFormat == "tsv"):
            return self.compareSV(resultPath, queryResult, resultFormat, test)
        return (False, "", "")
            
    def compareSV(self, resultPath, queryResult, resultFormat, test):
        with open(resultPath, "r") as resultFile:
            expectedResult = self.csvAndTsvtoArray(resultFile.read(), resultFormat)
        result = self.csvAndTsvtoArray(queryResult[1], resultFormat)
        self.testData[test[2]]["expected"] = str(expectedResult).replace("<", "&lt;").replace(">", "&gt;").replace("],", "],\n")
        self.testData[test[2]]["got"] = str(result).replace("<", "&lt;").replace(">", "&gt;").replace("],", "],\n")
        resultCopy = result.copy()  
        expectedResultCopy = expectedResult.copy()
        for row1 in result:
            equal = False
            row2Delete = None
            for row2 in expectedResult:
                if self.compareRows(row1, row2):
                    equal = True
                    row2Delete = row2
                    break
            if equal:
                resultCopy.remove(row1)
                expectedResultCopy.remove(row2Delete)
        
        if len(resultCopy) == 0 and len(expectedResultCopy) == 0:
            return (True, expectedResultCopy, resultCopy)
        else:
            return (True, expectedResultCopy, resultCopy)

    def compareJSON(self, result: dict, expected: dict):
        """
            Compare two dictionaries by deleting identical elements from the dictionaries
            If the resulting dictionaries are empty return True
        """
        resultCopy = dict(result)
        expectedCopy = dict(expected)
        # Compare the head
        if expected["head"]["vars"] != result["head"]["vars"]:
            if len(expected["head"]["vars"]) != len(result["head"]["vars"]):
                return (False, expectedCopy, resultCopy)
            for var in expected["head"]["vars"]:
                if var not in result["head"]["vars"]:
                    return (False, expectedCopy, resultCopy)
        del resultCopy["head"]
        del expectedCopy["head"]

        # Compare the results
        if len(
                expected["results"]["bindings"]) != len(
                result["results"]["bindings"]):
            return (False, expectedCopy, resultCopy)
        for i in range(len(expected["results"]["bindings"])):
            for j in range(len(resultCopy["results"]["bindings"])):
                if expected["results"]["bindings"][i].keys(
                ) == resultCopy["results"]["bindings"][j].keys():
                    keys = list(expected["results"]["bindings"][i].keys())
                    for keyID in range(len(keys)):
                        if not self.compareDictionaries(
                                expected["results"]["bindings"][i][keys[keyID]], resultCopy["results"]["bindings"][j][keys[keyID]]):
                            break
                        if keyID == len(keys) - 1:
                            for x in range(len(keys)):
                                del resultCopy["results"]["bindings"][j][keys[x]]
                                del expectedCopy["results"]["bindings"][i][keys[x]]

            for x in range(len(resultCopy["results"]["bindings"])):
                if resultCopy["results"]["bindings"][x]:
                    break
                if x == len(resultCopy["results"]["bindings"]) - 1:
                    del resultCopy["results"]

            for y in range(len(expectedCopy["results"]["bindings"])):
                if expectedCopy["results"]["bindings"][y]:
                    break
                if y == len(expectedCopy["results"]["bindings"]) - 1:
                    del expectedCopy["results"]

        if not expectedCopy and not resultCopy:
            return (True, expectedCopy, resultCopy)
        else:

            return (False, expectedCopy, resultCopy)

    def runTests(self):
        for graph in self.testsOfGraph:
            graphPath = self.pathToTestSuite + graph
            print(graphPath)
            status = "Failed"
            errorType = ""

            self.stopServer()
            self.removeIndex()
            indexMessage = self.index(graphPath)
            if indexMessage.find("Index build completed") == -1:
                errorType = "INDEX BUILD ERROR"
                for test in self.testsOfGraph[graph]:
                    self.testData[test[2]]["indexLog"] = str(indexMessage)
                    self.testData[test[2]]["status"] = status
                    self.testData[test[2]]["errorType"] = errorType
                    self.testData[test[2]]["status"] = "Failed"
                continue

            serverResult = self.startSever()
            if serverResult[0] != 200:
                errorType = "SERVER ERROR"
                self.testData[test[2]]["status"] = status
                self.testData[test[2]]["errorType"] = errorType
                continue

            for test in self.testsOfGraph[graph]:
                typeName = self.testData[test[2]]["typeName"]
                self.testData[test[2]]["indexLog"] = str(indexMessage)
                queryPath = self.pathToTestSuite + self.testData[self.testsOfGraph[graph][0][2]]["path"] + test[0]
                resultPath = self.pathToTestSuite + self.testData[self.testsOfGraph[graph][0][2]]["path"] + test[1]
                print(queryPath)
                queryString = self.readFile(queryPath).replace("\n", " ")
                self.testData[test[2]]["querySent"] = queryString
                resultFormat = test[1][test[1].rfind(".") + 1:]
                queryResult = self.query(queryString, resultFormat)

                if queryResult[0] == 200:

                    result = self.compare(resultPath, queryResult, test, typeName, resultFormat)
                    self.testData[test[2]]["expectedDif"] = str(result[1])
                    self.testData[test[2]]["resultDif"] = str(result[2])
                    if result[0]:
                        status = "Passed"
                    else:
                        errorType = "RESULTS NOT THE SAME"
                else:
                    errorType = "Undefined error"
                    if queryResult[1].find("exception") != -1:
                        errorType = "QUERY EXCEPTION"
                    if queryResult[1].find("HTTP Request") != -1:
                        errorType = "REQUEST ERROR"
                    self.testData[test[2]]["queryLog"] = str(queryResult[1])

                if typeName == "PositiveSyntaxTest11" or typeName == "NegativeSyntaxTest11":
                    if typeName == "PositiveSyntaxTest11":
                        if errorType != "":
                            status = "Failed"
                        else:
                            status = "Passed"
                            errorType = ""
                    if typeName == "NegativeSyntaxTest11":
                        if errorType == "QUERY EXCEPTION":
                            status = "Passed"
                            errorType = ""
                        else:
                            status = "Failed"
                            errorType = "EXPECTED: QUERY EXCEPTION ERROR"
                self.testData[test[2]]["status"] = status
                self.testData[test[2]]["errorType"] = errorType
                if status == "Passed":
                    self.passed += 1
                elif status == "Failed":
                    self.failed += 1

        self.removeIndex()

    def extractTests(self, file):
        # Currently only for the folder aggregates
        dirPaths = self.readFile("directories.txt").split("\n")
        queries = ["Query.rq","Syntax.rq","Protocol.rq","Update.rq"]
        outputCsvPath = file
        csvRows = []

        for path in dirPaths:
            print(path)
            self.removeIndex()
            self.index(self.pathToTestSuite + path + "/manifest.ttl")
            self.startSever()
            for query in queries:
                query = self.query(self.readFile(query), "csv")
                if query[0] == 200:
                    csv_content = query[1]

                    csvReader = csv.reader(csv_content.splitlines())
                    next(csvReader)
                    for row in csvReader:
                        csvRows.append(row)
            self.stopServer()
        with open(outputCsvPath, "w", newline="") as csvfile:
            csv_writer = csv.writer(csvfile)
            csv_writer.writerows(csvRows)

    def generateJSONFile(self):
        filePath = "./www/RESULTS.json"
        if os.path.exists(filePath):
            with open(filePath, 'r') as file:
                data = json.load(file)
        else:
            data = {}
        data[self.name] = self.testData
        data[self.name]["info"] = { "name" : "info",
                                    "passed" : self.passed,
                                    "tests" : self.tests,
                                    "failed" : self.failed}
        with open(filePath, 'w') as file:
            json.dump(data, file, indent=4)

    def jsonToDict(self, string):
        json_dict = json.loads(string)
        return json_dict

    def xmlToDict(self, file):
        tree = ElementTree.parse(file)
        root = tree.getroot()
        # Define the XML namespace
        ns = {"sparql": "http://www.w3.org/2005/sparql-results#"}

        # Init the output dictionary
        output = {"head": {"vars": []}, "results": {"bindings": []}}

        # head
        head = root.find("sparql:head", ns)
        if head is not None:
            for variable in head.findall("sparql:variable", ns):
                name = variable.attrib["name"]
                output["head"]["vars"].append(name)

        # results
        results = root.find("sparql:results", ns)
        if results is not None:
            for result in results.findall("sparql:result", ns):
                binding_dict = {}
                for binding in result.findall("sparql:binding", ns):
                    name = binding.attrib["name"]
                    value = {}

                    # URI
                    uri = binding.find("sparql:uri", ns)
                    if uri is not None:
                        value["type"] = "uri"
                        value["value"] = uri.text

                    # Literal
                    literal = binding.find("sparql:literal", ns)
                    if literal is not None:
                        value["type"] = "literal"
                        value["value"] = literal.text
                        datatype = literal.get("datatype", "")
                        if datatype != "":
                            value["datatype"] = datatype

                    binding_dict[name] = value

                output["results"]["bindings"].append(binding_dict)

        return output

    def csvAndTsvtoArray(self, string, type):
        result = []

        with StringIO(string) as io:
            delimiter = "," if type == "csv" else "\t"  # Determine the delimiter
            csvReader = csv.reader(io, delimiter=delimiter)
            for row in csvReader:
                result.append(row)

        return result

def main():
    args = sys.argv[1:]
    if len(args) != 3:
        print(f"Usage to extract tests: python3 {sys.argv[0]} <path to binaries> <file> extract\n Usage to extract tests: python3 {sys.argv[0]} <path to binaries> <file> <name of the run>)")
        sys.exit()
    testSuite = TestSuite(args[0], args[2])
    if args[2] == "extract":
        print("GET TESTS!")
        testSuite.extractTests(args[1])
    else:
        print("RUN TESTS!")
        testSuite.initializeTests(args[1])
        testSuite.runTests()
        testSuite.generateJSONFile()
    print("DONE!")


if __name__ == "__main__":
    main()
