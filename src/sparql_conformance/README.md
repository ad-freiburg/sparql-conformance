# qlever-control integration

This directory is the `sparql_conformance` package: the same conformance-test harness as the [repository root](../../README.md), wired into the [qlever-control](https://github.com/ad-freiburg/qlever-control) CLI so it can be run as `sparql_conformance <command>` against QLever and six other engines out of the box, without writing an `EngineManager` yourself.

The `sparql_conformance` console script is installed by this package, but it
loads qlever-control lazily. To test local changes in sibling checkouts,
install both projects in editable mode, with qlever-control first:

```bash
python -m pip install -e ../qlever-control
python -m pip install -e .
```

The second command is important when upgrading from a qlever-control revision
that also provided the `sparql_conformance` executable. During that upgrade,
pip removes the shared executable; reinstalling sparql-conformance recreates
it with a single owning package. From a sparql-conformance checkout, the
equivalent second command is `python -m pip install -e .`. The CLI can also be
run without its generated executable as
`python -m sparql_conformance visualize`.

To test the pushed integration branch instead of local qlever-control changes,
replace the first editable-install command with:

```bash
python -m pip install \
  "git+https://github.com/SIRDNARch/qlever-control.git@sparql-conformance-command-all-engines"
```

Without qlever-control, the independent `sparql-conformance --engine
/path/to/manager.py ...` workflow remains available.

### How the integrated CLI is split between the packages

When both packages are installed, they cooperate rather than either package
containing a copy of the other:

```text
sparql_conformance analyze
  -> executable owned by sparql-conformance
  -> qlever-control parses the Qleverfile and dispatches the command
  -> AnalyzeCommand is loaded from sparql_conformance.commands
  -> the selected engine manager uses qlever-control to operate the engine
```

In other words, sparql-conformance owns the executable and the conformance
command implementations. qlever-control supplies the reusable CLI/Qleverfile
framework and the engine-management commands. Its command discovery uses
Python imports, allowing it to find `sparql_conformance.commands` in the
separately installed package, including in editable installations.

## Quickstart

Each engine run lives in its own directory (it holds that engine's `Qleverfile` and downloaded test suite):

```bash
mkdir qlever && cd qlever
sparql_conformance setup qlever      # writes a Qleverfile, downloads the W3C test suite
sparql_conformance test              # runs it, writes ./results/qlever.json.bz2
```

Supported engine names for `setup`: `qlever`, `blazegraph`, `graphdb`, `jena`, `mdb`, `oxigraph`, `virtuoso`. The `--engine` option accepts the same names plus `qlever-binaries`.

## Commands

### `setup <engine>`

Writes a pre-configured `Qleverfile` for the given engine into the current directory and downloads the W3C test suite (sparse checkout of `sparql/sparql11` and `sparql/sparql10` from [w3c/rdf-tests](https://github.com/w3c/rdf-tests)) into `./testsuite-files`. Run once per engine directory.

```bash
mkdir jena && cd jena
sparql_conformance setup jena
```

### `test`

Runs the configured test suites against the engine and writes one result file.

```bash
sparql_conformance test
```

| Argument | Default | Description |
|---|---|---|
| `--engine` | from Qleverfile | Engine type: `qlever`, `qlever-binaries`, `blazegraph`, `graphdb`, `jena`, `mdb`, `oxigraph`, `virtuoso` |
| `--name` | from Qleverfile | Run name; output is written to `<results-dir>/<name>.json.bz2` |
| `--port` | from Qleverfile | Port the engine server listens on |
| `--graph-store` | engine-specific | Optional override for the engine manager's graph store endpoint |
| `--test-suites` | from Qleverfile | JSON object mapping suite names to directories, e.g. `'{"sparql11":"./testsuite-files/sparql/sparql11/","my-suite":"/path/to/custom"}'` |
| `--type-alias` | from Qleverfile | JSON list of XSD type pairs treated as equivalent deviations, e.g. `'[["http://.../integer","http://.../int"]]'` |
| `--exclude` | — | Comma-separated test/group names to skip |
| `--include` | — | Comma-separated test/group names to run (all others skipped) |
| `--binaries-directory` | — | Path to `qlever-index`/`qlever-server` binaries (native `qlever`/`qlever-binaries` engine only) |
| `--results-dir` | `./results` | Directory for the output JSON file |
| `--report` | `none` | Console verbosity: `none`, `summary`, or `line` (see below) |
| `--compare-to` | — | Path to a previous `<name>.json.bz2` run to diff against |

Examples:

```bash
# Only run the aggregates group
sparql_conformance test --include aggregates

# Readable console output while running
sparql_conformance test --report line

# Override the configured suites with standard and custom directories
sparql_conformance test --test-suites '{"sparql11":"../rdf-tests/sparql/sparql11","vendor":"../vendor-tests"}'

# Compare this run against a previous one; prints regressions and fixes
sparql_conformance test --compare-to results/old-run.json.bz2
```

### `analyze <test-name> [<test-name> ...]`

Starts the engine with the given test's data loaded, then blocks so you can send it queries by hand (e.g. via `curl` or the engine's own UI) to debug a failure. Press Ctrl-C or answer the prompt to shut it down.

```bash
sparql_conformance analyze "COUNT 1" "COUNT 2"
```

Takes the same `--engine`, `--test-suites`, `--type-alias`, `--exclude`, and `--binaries-directory` arguments as `test` (see above); `--include` is not needed since the test names are given as positional arguments.

In a Qleverfile, configure the mapping as JSON without shell quotes:

```ini
TEST_SUITES = {"sparql11": "./testsuite-files/sparql/sparql11/", "sparql10": "./testsuite-files/sparql/sparql10/"}
```

`--test-suites` replaces `--sparql11-dir`, `--sparql10-dir`, and `--custom`; those old arguments and Qleverfile keys are no longer accepted.

### `visualize`

Starts the [sparql-conformance-ui](https://github.com/ad-freiburg/sparql-conformance-ui) web viewer via docker/podman compose, serving the result files in the current directory.

```bash
sparql_conformance visualize
```

| Argument | Default | Description |
|---|---|---|
| `--port` | `3000` | Port to serve the UI on |
| `--result-directory` | current directory | Directory containing `*.json.bz2` result files to display |
| `--ui-branch` | `main` | Branch of `sparql-conformance-ui` to build |

Then open `http://localhost:3000`.

## Console output

By default a run only writes the result file; `--report` adds terminal feedback:

| `--report` | What it prints |
|---|---|
| `none` (default) | Nothing extra. |
| `summary` | End-of-run totals (passed / failed / intended / not tested) plus a list of failed tests. |
| `line` | A live colored `PASS`/`FAIL`/`INTD` line per test, plus the summary. |

## Adding a new engine

Adding an engine to `sparql_conformance` needs two things:

1. The engine must already be a qlever-control target (its own `q<engine>` CLI, e.g. `qjena`).
2. An `EngineManager` subclass under [`engines/`](engines/) that calls that CLI's commands (see [`engines/README.md`](engines/README.md) for the adapter contract) — for example [`engines/qlever.py`](engines/qlever.py) drives `qlever`'s `index`/`start`/`stop`/`query` commands.

Then register it in the `_MANAGERS` map in [`engines/__init__.py`](engines/__init__.py) and add a `Qleverfile.<engine>` under [`Qleverfiles/`](Qleverfiles/) for `setup` to install.
