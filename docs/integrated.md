# Built-in engines and integrated CLI

The `sparql_conformance <command>` interface connects this harness to
[qlever-control](https://github.com/ad-freiburg/qlever-control). It runs QLever
and six other engines without requiring a custom `EngineManager`.

It requires Python 3.10 or newer, Git, a running Docker or Podman service, and
the matching qlever-control integration. While that integration is pending
upstream, follow the [temporary branch installation guide](pending-qlever-control.md).
The independent `sparql-conformance --engine /path/to/manager.py ...` workflow
does not require qlever-control.

The `sparql_conformance` executable is owned by this package and loads
qlever-control lazily. It can also be invoked as
`python -m sparql_conformance <command>`.

## How the integrated CLI is split between the packages

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

## Supported engines

The `setup` command supports `qlever`, `blazegraph`, `graphdb`, `jena`, `mdb`,
`oxigraph`, and `virtuoso`. The `--engine` option accepts the same names plus
`qlever-binaries`, which uses locally compiled QLever binaries. GraphDB also
requires a valid GraphDB license.

Follow the [root quickstart](../README.md#quickstart-with-a-built-in-engine) for
the shortest complete run. Keep each engine in its own working directory
because that directory stores its `Qleverfile`, downloaded suites, engine work
files, and results.

## Commands

### `setup <engine>`

Writes a preconfigured `Qleverfile` for the selected engine and downloads a
sparse checkout of `sparql/sparql11` and `sparql/sparql10` from
[w3c/rdf-tests](https://github.com/w3c/rdf-tests) into `./testsuite-files`.
Run it once per engine directory.

```bash
mkdir jena && cd jena
sparql_conformance setup jena
```

`setup` refuses to overwrite an existing `Qleverfile` or test-suite checkout.
Use a new directory, or deliberately remove the old generated files before
running it again.

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
| `--system` | from Qleverfile | Container command (`docker` or `podman`) or `native` |
| engine image options | from Qleverfile | Override the selected engine's container image |

qlever-control also adds `--show` and `--log-level` to every integrated
command. Run `sparql_conformance test --help` for the complete, current option
list.

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

Starts the engine with the selected test data loaded, then waits while you send
queries manually using `curl` or the engine's UI. Press Ctrl-C or answer the
prompt to shut it down.

```bash
sparql_conformance analyze "COUNT 1" "COUNT 2"
```

Takes the same engine, suite, runtime, image, type-alias, exclusion, and binary
configuration as `test`; `--include` is not needed because the test names are
given as positional arguments. Run `sparql_conformance analyze --help` for the
complete option list.

In a Qleverfile, configure the mapping as JSON without shell quotes:

```ini
TEST_SUITES = {"sparql11": "./testsuite-files/sparql/sparql11/", "sparql10": "./testsuite-files/sparql/sparql10/"}
```

`--test-suites` replaces `--sparql11-dir`, `--sparql10-dir`, and `--custom`;
those old arguments and Qleverfile keys are no longer accepted.

### `visualize`

Starts the [sparql-conformance-ui](https://github.com/ad-freiburg/sparql-conformance-ui)
web viewer using Docker Compose or Podman Compose. It recursively imports
supported result files from the selected directory.

```bash
sparql_conformance visualize
```

From a normal engine directory, either the default current directory or an
explicit `--result-directory ./results` finds the generated results.

| Argument | Default | Description |
|---|---|---|
| `--port` | `3000` | Port to serve the UI on |
| `--result-directory` | current directory | Directory containing `*.json.bz2` result files to display |
| `--ui-branch` | `main` | Branch of `sparql-conformance-ui` to build |

Then open `http://localhost:3000`.

The selected UI branch is resolved and built on every launch so moving branches
such as `main` stay current. Docker reuses unchanged build layers.

## Console output

By default a run only writes the result file; `--report` adds terminal feedback:

| `--report` | What it prints |
|---|---|
| `none` (default) | Nothing extra. |
| `summary` | End-of-run totals (passed / failed / intended / not tested) plus a list of failed tests. |
| `line` | A live colored `PASS`/`FAIL`/`INTD` line per test, plus the summary. |

## Adding a new engine

Adding an engine to `sparql_conformance` needs two things:

1. The engine must already be a qlever-control target with its own `q<engine>`
   CLI, such as `qjena`.
2. Add an `EngineManager` under
   [`src/sparql_conformance/engines/`](../src/sparql_conformance/engines/) that
   calls that CLI's commands; see the [adapter contract](engine-adapters.md).
   For example, [`qlever.py`](../src/sparql_conformance/engines/qlever.py)
   drives QLever's `index`, `start`, `stop`, and `query` commands.

Register it in `_MANAGERS` in
[`engines/__init__.py`](../src/sparql_conformance/engines/__init__.py), then add
a `Qleverfile.<engine>` under
[`Qleverfiles/`](../src/sparql_conformance/Qleverfiles/) for `setup` to install.
