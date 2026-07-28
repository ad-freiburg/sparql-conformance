# sparql-conformance

Run W3C SPARQL conformance suites against a SPARQL engine and write a
machine-readable result file. The harness covers queries, updates, syntax,
SPARQL Protocol, and Graph Store Protocol tests.

You can use it in two ways:

- Run the standalone CLI with your own small engine adapter.
- Install qlever-control for ready-made support for QLever, Blazegraph,
  GraphDB, Jena, MillenniumDB, Oxigraph, and Virtuoso.

## How do I start?

The quickest useful run uses qlever-control, so you do not need to
install or start a SPARQL server:

Until the changes are merged upstream, use the
`SIRDNARch/sparql-conformance-command-all-engines` branch of qlever-control.
The [pending-branch guide](QLEVER_CONTROL_GETTING_STARTED.md) contains the
exact clone commands.

Install qlever-control and this package in the same environment, with
qlever-control first:

```bash
python -m pip install -e ../qlever-control
python -m pip install -e .

mkdir qlever-conformance
cd qlever-conformance
sparql_conformance setup qlever
sparql_conformance test --report summary
```

`setup` creates the engine's `Qleverfile` and downloads the W3C suites. Keep a
separate working directory for each engine.

## Documentation

- [Standalone CLI and result format](docs/standalone.md)
- [Built-in engines and integrated commands](src/sparql_conformance/README.md)
- [Writing an engine adapter](src/sparql_conformance/engines/README.md)
- [Working with the pending qlever-control branches](QLEVER_CONTROL_GETTING_STARTED.md)
- [Result viewer](https://github.com/SIRDNARch/sparql-conformance-ui)

## Development

Requires Python 3.9 or newer.

```bash
python -m pip install -e ".[dev]"
pytest
ruff format --check
ruff check
```

The standalone runner does not require qlever-control. Tests for the optional
integration verify that this package boundary remains intact.
