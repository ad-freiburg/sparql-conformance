# qlever-test-suite
SPARQL test suite (https://www.w3.org/2009/sparql/docs/tests/)<br>
for QLEVER (https://github.com/ad-freiburg/qlever) <br>
# How to use the qlever-test-suite
You need the QLever code.<br>
Clone this repository.<br>
Extract the tests with:<br>
```
python3 testsuite.py [relative path to your qlever code binaries] [file name] extract
```
<br>
Example: python3 testsuite.py ../qlever-code/build listOfTests.csv extract<br>
This will create a file consisting of all tests.<br>
You can run those tests with:<br>

```
python3 testsuite.py [relative path to your qlever code binaries] [file name] [name for the test suite run]
```

<br>
Example: python3 testsuite.py ../qlever-code/build listOfTests.csv first-test<br>

Start the sever:<br>
```
python3 server.py
```
<br>
open http://localhost:8000/www/index.html
