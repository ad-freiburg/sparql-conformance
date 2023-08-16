import os
import sys
import time
import csv
import requests
from io import StringIO
from xml.etree import cElementTree as ElementTree
import json

PATH_TO_TESTS = "./TestSuite/sparql11-test-suite/"


def jsonToDict(string):
    json_dict = json.loads(string)
    return json_dict

def xmlToDict(file):
    tree = ElementTree.parse(file)
    root = tree.getroot()
    # Define the XML namespace
    ns = {'sparql': 'http://www.w3.org/2005/sparql-results#'}

    # Init the output dictionary
    output = {'head': {'vars': []}, 'results': {'bindings': []}}

    # head
    head = root.find('sparql:head', ns)
    if head is not None:
        for variable in head.findall('sparql:variable', ns):
            name = variable.attrib['name']
            output['head']['vars'].append(name)

    # results
    results = root.find('sparql:results', ns)
    if results is not None:
        for result in results.findall('sparql:result', ns):
            binding_dict = {}
            for binding in result.findall('sparql:binding', ns):
                name = binding.attrib['name']
                value = {}

                # URI
                uri = binding.find('sparql:uri', ns)
                if uri is not None:
                    value['type'] = 'uri'
                    value['value'] = uri.text

                # Literal
                literal = binding.find('sparql:literal', ns)
                if literal is not None:
                    value['type'] = 'literal'
                    value['value'] = literal.text
                    value['datatype'] = literal.attrib['datatype']

                binding_dict[name] = value

            output['results']['bindings'].append(binding_dict)

    return output

def csvAndTsvtoArray(string, type):
    result = []

    with StringIO(string) as io:
        delimiter = ',' if type == "csv" else '\t'  # Determine the delimiter
        csvReader = csv.reader(io, delimiter=delimiter)
        for row in csvReader:
            result.append(row)

    return result

class TestSuite:
    def __init__(self, file):
        self.testData = {}
        # SOFT PASSED
        self.alias = {
            'http://www.w3.org/2001/XMLSchema#integer': 'http://www.w3.org/2001/XMLSchema#int',
            'http://www.w3.org/2001/XMLSchema#double': 'http://www.w3.org/2001/XMLSchema#decimal'}
        self.testsOfGraph = {}
        try:
            with open(file) as csvFile:
                csvReader = csv.reader(csvFile)
                # row:
                # test,type,name,feature,comment,approval,approvedBy,query,data,result
                for row in csvReader:
                    if row[8] in self.testsOfGraph:
                        self.testsOfGraph[row[8]].append([row[7], row[9], row[2]])
                    else:
                        self.testsOfGraph[row[8]] = [[row[7], row[9], row[2]]]
                    
                    # Extract folder the test is located in
                    lastSlashIndex = row[0].rfind("/")
                    secondLastSlashIndex = row[0].rfind("/", 0, lastSlashIndex - 1)
                    pathToTest = row[0][secondLastSlashIndex + 1: lastSlashIndex + 1]
                    # Extract test type
                    lastHashtagIndex = row[1].rfind("#")
                    typeOfTest = row[1][lastHashtagIndex + 1:]
                    self.testData[row[2]] = {'test': row[0],
                                            'type': row[1],
                                            'typeName' : typeOfTest,
                                            'name': row[2],
                                            'path' : pathToTest,
                                            'feature': row[3],
                                            'comment': row[4],
                                            'approval': row[5],
                                            'approvedBy': row[6],
                                            'query': row[7],
                                            'graph': row[8],
                                            'result': row[9],
                                            'status': '',
                                            'errorType': '',
                                            'errorMessage': '',
                                            'expected': '',
                                            'got': '',
                                            'indexLog': '',
                                            'serverLog': '',
                                            'serverStatus': '',
                                            'queryLog': '',
                                            'querySent' : ''}
        except:
            pass

    def readFile(self, file):
        data = open(file).read().replace('\n', ' ')
        return data

    def index(self, graphPath):
        index = os.popen(
            f'ulimit -Sn 1048576; cat {graphPath} | ../qlever-code/build/IndexBuilderMain -F ttl -f - -i TestSuite -s TestSuite.settings.json | tee TestSuite.index-log.txt')
        return index.read()

    def removeIndex(self):
        os.popen('rm -f TestSuite.index.* TestSuite.vocabulary.* TestSuite.prefixes TestSuite.meta-data.json TestSuite.index-log.txt')

    def startSever(self):
        start = os.popen(
            '../qlever-code/build/ServerMain -i TestSuite -j 8 -p 7001 -m 4 -c 2 -e 1 -k 100 -a "TestSuite_3139118704" > TestSuite.server-log.txt &')
        # Wait for the server to be ready
        maxRetries = 8  # Maximum number of retries
        retryInterval = 0.25  # Time interval between retries in seconds
        url = 'http://mint-work:7001'
        headers = {
            'Content-type': 'application/sparql-query'
        }
        testQuery = "SELECT ?s ?p ?o { ?s ?p ?o } LIMIT 1"
        for i in range(maxRetries):
            try:
                response = requests.post(url, headers=headers, data=testQuery)
                if response.status_code == 200:
                    break
            except requests.exceptions.RequestException:
                pass 
            time.sleep(retryInterval)
        else:
            return (500, response.text)

        return (200, "")

    def stopServer(self):
        os.popen(
            'pkill -f "../qlever-code/build/ServerMain -i [^ ]*TestSuite"')

    def query(self, query, resultFile):
        """ 
            Function sends query to qlever-server and returns a tuple consisting of the status code and message
            type specifies the returned format of the http request
        """
        resultFormat = resultFile[resultFile.rfind(".") + 1:]
        if resultFormat == "csv":
            type = 'text/csv'
        elif resultFormat == "tsv":
            type = 'text/tab-separated-values'
        else:
            type = 'application/sparql-results+json'
        url = 'http://mint-work:7001'
        headers = {
            'Accept': f'{type}',
            'Content-type': 'application/sparql-query'
        }
        response = requests.post(url, headers=headers, data=query)

        return (response.status_code, response.text)

    def compareRows(self, row1, row2):
        if len(row1) != len(row2):
            return False

        for element1, element2 in zip(row1, row2):
            if not self.compareValues(element1.split("^")[0], element2.split("^")[0]):
                return False
        return True

    def compareValues(self, value1: str, value2: str):
        # In most cases the values are in the same representation
        if value1 == value2:
            return True
        # Handle exceptions ex. 30000 == 3E4
        if value1[0].isnumeric():
            if float(value1) == float(value2):
                return True
        else:  # Handle exceptions integer = int
            if value1 in self.alias and self.alias[value1] == value2:
                return True
        return False

    def compareDictionaries(self, dict1, dict2) -> bool:
        dict1Copy = dict(dict1)
        dict2Copy = dict(dict2)
        # Remove the key from the dictionaries if it exists and 
        # has the same value
        for key, value in dict1.items():
            if key in dict2Copy:
                if self.compareValues(value, dict2Copy[key]):
                    del dict2Copy[key]
                    del dict1Copy[key]
        return not dict1Copy and not dict2Copy

    def compare(self, resultPath, queryResult, test, typeName, resultFormat):
        if typeName == "QueryEvaluationTest" and resultFormat == "srx":
            jsonDict = jsonToDict(queryResult[1])
            xmlDict = xmlToDict(resultPath)
            self.testData[test[2]]["expected"] = str(xmlDict)
            self.testData[test[2]]["got"] = str(jsonDict)
            return self.compareJSON(jsonDict, xmlDict)
        elif resultFormat == "csv" or resultFormat == "tsv":
            return self.compareSV(resultPath, queryResult, resultFormat, test)
            
    def compareSV(self, resultPath, queryResult, resultFormat, test):
        with open(resultPath, 'r') as resultFile:
            expectedResult = csvAndTsvtoArray(resultFile.read(), resultFormat)
        result = csvAndTsvtoArray(queryResult[1], resultFormat)
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
            return True
        else:
            return False

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
                return False
            for var in expected["head"]["vars"]:
                if var not in result["head"]["vars"]:
                    return False
        del resultCopy["head"]
        del expectedCopy["head"]

        # Compare the results
        if len(
                expected["results"]["bindings"]) != len(
                result["results"]["bindings"]):
            return False
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
            return True
        else:
            return False

    def runTests(self):
        for graph in self.testsOfGraph:
            graphPath = PATH_TO_TESTS + self.testData[self.testsOfGraph[graph][0][2]]["path"] + graph
            status = "Failed"
            errorMessage = ""

            self.stopServer()
            self.removeIndex()
            indexMessage = self.index(graphPath)
            if indexMessage.find("Index build completed") == -1:
                errorMessage = "INDEX BUILD ERROR"
                for test in self.testsOfGraph[graph]:
                    self.testData[test[2]]["indexLog"] = str(indexMessage)
                    self.testData[test[2]]["status"] = status
                    self.testData[test[2]]["errorMessage"] = errorMessage
                    self.testData[test[2]]["status"] = "Failed"
                continue

            serverResult = self.startSever()
            if serverResult[0] != 200:
                errorMessage = "SERVER ERROR"
                self.testData[test[2]]["status"] = status
                self.testData[test[2]]["errorMessage"] = errorMessage
                continue

            for test in self.testsOfGraph[graph]:
                typeName = self.testData[test[2]]["typeName"]
                self.testData[test[2]]["indexLog"] = str(indexMessage)
                queryPath = PATH_TO_TESTS + self.testData[self.testsOfGraph[graph][0][2]]["path"] + test[0]
                resultPath = PATH_TO_TESTS + self.testData[self.testsOfGraph[graph][0][2]]["path"] + test[1]

                queryString = self.readFile(queryPath)
                self.testData[test[2]]["querySent"] = queryString
                resultFormat = test[1][test[1].rfind(".") + 1:]
                queryResult = self.query(queryString, resultFormat)

                if queryResult[0] == 200:
                    if self.compare(resultPath, queryResult, test, typeName, resultFormat):
                        status = "Passed"
                    else:
                        errorMessage = "RESULTS NOT THE SAME"
                else:
                    errorMessage = "Undefined error"
                    if queryResult[1].find("exception") != -1:
                        errorMessage = "QUERY EXCEPTION"
                    if queryResult[1].find("HTTP Request") != -1:
                        errorMessage = "REQUEST ERROR"
                    self.testData[test[2]]["queryLog"] = str(queryResult[1])

                self.testData[test[2]]["status"] = status
                self.testData[test[2]]["errorMessage"] = errorMessage

    def extractTests(self):
        # Currently only for the folder aggregates
        folderPaths = ["aggregates/", "csv-tsv-res/"]
        queries = ["queryeval.rq", "csvformat.rq"]
        outputCsvPath = 'listOfTests.csv'
        csvRows = []

        for path in folderPaths:
            self.removeIndex()
            self.index(PATH_TO_TESTS + path + "manifest.ttl")
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

        with open(outputCsvPath, 'w', newline='') as csvfile:
            csv_writer = csv.writer(csvfile)
            csv_writer.writerows(csvRows)

    def generateJSONFile(self):
        # Convert the dictionary to a JSON string
        # `indent` parameter adds readability
        json_string = json.dumps(self.testData, indent=4)

        with open("RESULTS.json", "w") as json_file:
            json_file.write(json_string)


def main():
    args = sys.argv[1:]
    if len(args) < 1 or len(args) > 2:
        print(f"Usage: python3 {sys.argv[0]} <file>")
        sys.exit()
    testSuite = TestSuite(args[0])
    if len(args) == 2:
        testSuite.extractTests()
    else:
        testSuite.runTests()
    testSuite.generateJSONFile()
    print("DONE!")


if __name__ == "__main__":
    main()


# https://stackoverflow.com/questions/2148119/how-to-convert-an-xml-string-to-a-dictionary
# https://www.xml.com/pub/a/2006/05/31/converting-between-xml-and-json.html
# ulimit -Sn 1048576; cat .ttl | ../qlever-code/build/IndexBuilderMain -F ttl -f - -i TestSuite -s TestSuite.settings.json | tee TestSuite.index-log.txt'
# ../../qlever-code/build/ServerMain -i TestSuite -j 8 -p 7001 -m 4 -c 2 -e 1 -k 100 -a "TestSuite_3139118704" > TestSuite.server-log.txt &
# pkill -f "../../qlever-code/build/ServerMain -i [^ ]*TestSuite"
# rm -f TestSuite.index.* TestSuite.vocabulary.* TestSuite.prefixes TestSuite.meta-data.json TestSuite.index-log.txt
# curl http://mint-work:7001 -H "Accept: text/tab-separated-values" -H
# "Content-type: application/sparql-query" --data "SELECT * WHERE { ?s ?p ?o } LIMIT 10"
