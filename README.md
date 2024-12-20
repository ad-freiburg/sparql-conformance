# qlever-test-suite

Running the [SPARQL test suite](https://www.w3.org/2009/sparql/docs/tests/) for [QLEVER](https://github.com/ad-freiburg/qlever).

## Prerequisites

You need too compile the [QLever code](https://github.com/ad-freiburg/qlever) and get the [SPARQL test suite files](https://github.com/w3c/rdf-tests/tree/main/sparql/).

## Running the test suite

### Create the config

Before you can run the test suite you have to setup the config. To do this run the following command.

```
python3 testsuite.py config <server address> <port> <path to testsuite> <path to the qlever binaries>  <graph store implementation host> <path of the URL of the graph store> <URL returned in the Location HTTP header>
```
Example:
```
python3 testsuite.py config http://0.0.0.0 7000 ./testsuite/ ../qlever-code/build/ localhost sparql sparql
```

### Extract the tests

After setting up the config you can now extract all the tests from the SPARQL test suite.

```
python3 testsuite.py extract
```

This will generate the test list with the specified name.

### Run

Now you can execute the test suite.

```
python3 testsuite.py <name for the test suite run>
```
Example:
```
python3 testsuite.py firstRun
```

If this is the first run it will generate a directory called results. All results will be saved in this directory. For example the firstRun.json.

### View and compare results

If you want to visualize the results you can use the TODO.
