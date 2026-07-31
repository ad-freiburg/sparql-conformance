# Standalone CLI

Use the standalone `sparql-conformance` command when you want to supply your
own engine adapter. It does not require qlever-control.

## Installation

```bash
python -m pip install -e .
git clone https://github.com/w3c/rdf-tests.git ../rdf-tests
```

## Basic usage

```bash
sparql-conformance \
  --engine ./my-engine-manager.py \
  --name my-run \
  --test-suites '{"sparql11":"../rdf-tests/sparql/sparql11"}'
```

`--test-suites` is an ordered JSON object. Its keys become suite names in the
result file, and its values are test-suite directories:

```bash
--test-suites '{"sparql11":"../rdf-tests/sparql/sparql11","vendor":"../vendor-tests"}'
```

Keep the JSON in single quotes in a shell so the inner double quotes reach the
application unchanged.

## Options

| Option | Default | Purpose |
|---|---|---|
| `--engine` | required | Python file containing an `EngineManager` subclass |
| `--name` | required | Run name and result filename |
| `--test-suites` | required | JSON mapping of suite names to directories |
| `--results-dir` | `./results` | Output directory |
| `--port` | `7001` | Engine server port |
| `--graph-store` | adapter default | Graph Store Protocol endpoint override |
| `--binaries-directory` | empty | Directory containing engine binaries |
| `--server-binary` | `qlever-server` | Server binary for the QLever binaries adapter |
| `--index-binary` | `qlever-index` | Index binary for the QLever binaries adapter |
| `--include` | all tests | Comma-separated test or group names to run |
| `--exclude` | none | Comma-separated test or group names to skip |
| `--type-alias` | none | JSON pairs of equivalent XSD types |
| `--report` | `none` | Console output: `none`, `summary`, or `line` |
| `--compare-to` | none | Previous result file used to report regressions and fixes |

`--test-suites` replaces the old `--sparql11-dir`, `--sparql10-dir`, and
`--custom` options.

## Common tasks

Run one group and print each result:

```bash
sparql-conformance \
  --engine ./my-engine-manager.py \
  --name aggregates \
  --test-suites '{"sparql11":"../rdf-tests/sparql/sparql11"}' \
  --include aggregates \
  --report line
```

Compare a run with an older result:

```bash
sparql-conformance \
  --engine ./my-engine-manager.py \
  --name new-run \
  --test-suites '{"sparql11":"../rdf-tests/sparql/sparql11"}' \
  --compare-to results/old-run.json.bz2
```

Treat two XSD types as an accepted equivalent:

```bash
--type-alias '[["http://www.w3.org/2001/XMLSchema#integer","http://www.w3.org/2001/XMLSchema#int"]]'
```

## Results

Each run writes `<results-dir>/<name>.json.bz2`, a bzip2-compressed JSON file
with one entry per test suite and an overall summary. Each test records its
status and, where applicable, HTML-formatted expected/actual differences for a
viewer such as
[`sparql-conformance-ui`](https://github.com/ad-freiburg/sparql-conformance-ui).

Console reporting is optional:

- `none` writes the result without extra per-test output.
- `summary` prints totals and a list of failures.
- `line` prints a live result for every test, followed by the summary.

Colors are disabled when output is not a terminal or `NO_COLOR` is set.

## Add an engine

An adapter is one Python file containing an `EngineManager` subclass. See
[Writing a custom EngineManager](../src/sparql_conformance/engines/README.md)
for the interface and the bundled rdflib example.
