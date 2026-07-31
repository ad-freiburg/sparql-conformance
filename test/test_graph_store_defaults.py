"""Tests for engine-owned Graph Store Protocol endpoint defaults."""

import pytest

from sparql_conformance.engines import get_engine_manager
from sparql_conformance.qlever_control import QleverControlRequiredError


@pytest.mark.parametrize(
    ("engine", "endpoint"),
    [
        ("qlever", "http-graph-store"),
        ("qlever-binaries", "http-graph-store"),
        ("blazegraph", "blazegraph/namespace/kb/sparql"),
        ("graphdb", "repositories/graphdb"),
        ("jena", "qlever-sparql-conformance/data"),
        ("mdb", "sparql"),
        ("oxigraph", "store"),
        ("virtuoso", "sparql"),
    ],
)
def test_builtin_engine_owns_graph_store_default(engine, endpoint):
    try:
        manager = get_engine_manager(engine)
    except QleverControlRequiredError:
        pytest.skip("built-in managers require the optional qlever-control package")

    assert manager.graph_store_endpoint() == endpoint
