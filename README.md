# qlever-test-suite
SPARQL test suite (https://www.w3.org/2009/sparql/docs/tests/) for QLEVER (https://github.com/ad-freiburg/qlever) 
You need the QLever code.
# How to use the qlever-test-suite
Clone this repository.
Extract the tests with: python3 testsuite.py [relative path to your qlever code binaries] [file name] extract
Example: python3 testsuite.py ../qlever-code/build listOfTests.csv extract
This will create a file consisting of all tests.
You can run those tests with: python3 testsuite.py [relative path to your qlever code binaries] [file name]
Example: python3 testsuite.py ../qlever-code/build listOfTests.csv
