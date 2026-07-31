"""Contract tests for preserving absolute named-graph IRIs in managers."""

from pathlib import Path

import pytest
import rdflib

from sparql_conformance.config import Config
from sparql_conformance.engines.engine_manager import has_uri_scheme

pytest.importorskip("qjena")
pytest.importorskip("qgraphdb")

from sparql_conformance.engines.graphdb_manager import (
    GraphdbManager,
    _ensure_base_iri,
)
from sparql_conformance.engines.jena_manager import JenaManager


def make_config():
    return Config(
        image=None,
        system="native",
        port="7001",
        graph_store="sparql",
        testsuite_dir=".",
        type_alias=[],
        binaries_directory="",
        exclude=[],
        include=None,
    )


@pytest.mark.parametrize(
    "iri",
    [
        "urn:example:graph",
        "file:///tmp/example-graph",
        "custom+v1:example",
    ],
)
def test_uri_scheme_detection_does_not_require_slashes(iri):
    assert has_uri_scheme(iri)


@pytest.mark.parametrize(
    ("manager", "needs_config"),
    [
        (JenaManager(), True),
        (GraphdbManager(), False),
    ],
)
@pytest.mark.parametrize("graph_iri", ["urn:example:graph", "file:///graph"])
def test_prepare_graphs_preserves_absolute_graph_iri(
    tmp_path,
    monkeypatch,
    manager,
    needs_config,
    graph_iri,
):
    monkeypatch.chdir(tmp_path)
    source = tmp_path / "source.ttl"
    source.write_text(
        "@prefix ex: <http://example.org/> . ex:s ex:p ex:o .\n"
    )
    graph_paths = ((str(source), graph_iri),)

    if needs_config:
        graph_files, cleanup_paths = manager._prepare_graphs(
            graph_paths,
            make_config(),
        )
    else:
        graph_files, cleanup_paths = manager._prepare_graphs(graph_paths)

    dataset = rdflib.Dataset()
    dataset.parse(graph_files[0], format="trig")
    identifiers = {str(graph.identifier) for graph in dataset.graphs()}
    assert graph_iri in identifiers

    manager._cleanup_graph_copies(cleanup_paths)


def test_jena_preserves_generated_query_directory_base():
    query = (
        "BASE <file:///suite/dataset/>\n"
        "SELECT * FROM <data.ttl> WHERE { ?s ?p ?o }"
    )

    assert JenaManager()._add_base_if_missing(make_config(), query) == query


def test_graphdb_preserves_generated_query_directory_base():
    query = (
        "BASE <file:///suite/dataset/>\n"
        "SELECT * FROM <data.ttl> WHERE { ?s ?p ?o }"
    )

    assert _ensure_base_iri(query) == query
