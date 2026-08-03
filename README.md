# sparql-conformance

Run the W3C SPARQL conformance suites against a SPARQL engine and write a
machine-readable result file. The harness covers queries, updates, syntax,
SPARQL Protocol, and Graph Store Protocol tests.

## Choose a command

The package installs two deliberately different command-line interfaces:

| Command | Use it for | Requirements |
|---|---|---|
| `sparql-conformance` | Running a custom, file-based engine adapter | Python 3.9 or newer |
| `sparql_conformance` | Running built-in engine integrations using Qleverfiles | Python 3.10 or newer, qlever-control, Git, and Docker or Podman |

The hyphenated command is standalone and does not require qlever-control. The
underscored command lets qlever-control start and operate QLever, Blazegraph,
GraphDB, Apache Jena Fuseki, MillenniumDB, Oxigraph, or Virtuoso for you.

## Quickstart with a built-in engine

The qlever-control integration is currently pending upstream. Follow the
[temporary installation guide](docs/pending-qlever-control.md) to install the
matching branch and this package in one virtual environment.

After installation, create a separate working directory for the engine run:

```bash
mkdir qlever-conformance
cd qlever-conformance
sparql_conformance setup qlever
sparql_conformance test --report summary
```

`setup` creates the engine's `Qleverfile` and downloads the W3C SPARQL 1.0 and
1.1 suites. The container runtime downloads and starts the selected engine.
Results are written below `./results`.

For a custom adapter instead, start with the
[standalone CLI guide](docs/standalone.md).

## Documentation

- [Standalone CLI](docs/standalone.md)
- [Built-in engines and integrated commands](docs/integrated.md)
- [Writing an engine adapter](docs/engine-adapters.md)
- [Result file format and status meanings](docs/results.md)
- [Temporary qlever-control branch installation](docs/pending-qlever-control.md)
- [Result viewer](https://github.com/ad-freiburg/sparql-conformance-ui)

## Development

The core package requires Python 3.9 or newer. Work on the qlever-control
integration requires Python 3.10 or newer.

```bash
python -m pip install -e ".[dev]"
pytest
ruff format --check
ruff check
```

The standalone runner does not require qlever-control. Tests for the optional
integration verify that this package boundary remains intact.
