# Test the pending qlever-control integration

Use this guide while the matching changes are still under review in the
`SIRDNARch` forks. For the command reference, see
[`src/sparql_conformance/README.md`](src/sparql_conformance/README.md).

## Prerequisites

- Git
- Python 3.10 or newer
- A running Docker or Podman service

## Install both branches

```bash
mkdir sparql-conformance-work
cd sparql-conformance-work

python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip

git clone https://github.com/SIRDNARch/qlever-control.git
git -C qlever-control switch sparql-conformance-command-all-engines

git clone https://github.com/ad-freiburg/sparql-conformance.git

python -m pip install -e ./qlever-control
python -m pip install -e ./sparql-conformance
```

Install qlever-control first. `sparql-conformance` owns the
`sparql_conformance` executable and must be installed last, particularly when
upgrading from an older qlever-control revision that installed an executable
with the same name.

Verify both CLIs:

```bash
qlever --help
sparql-conformance --help
sparql_conformance --help
```

The hyphenated command is the standalone runner. The underscored command is the
Qleverfile-based integration.

## Run QLever

Use a separate working directory for each engine:

```bash
mkdir qlever-run
cd qlever-run

sparql_conformance setup qlever
sparql_conformance test --report summary
```

`setup` writes `./Qleverfile` and downloads the W3C SPARQL 1.0 and 1.1 suites
below `./testsuite-files`. The test result is written below `./results`.

For a live result line per test, use `--report line`. To inspect a failure with
the engine left available for manual queries, run:

```bash
sparql_conformance analyze "TEST NAME"
```
