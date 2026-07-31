"""Regression tests for the bundled RWStore templates: the Blazegraph
manager used to resolve them via the old qlever-control repo layout
(<repo>/src/qblazegraph/), a path that does not exist in this repo."""

from pathlib import Path

import pytest

import sparql_conformance

DATA_DIR = Path(sparql_conformance.__file__).parent / "data"


def test_rwstore_templates_are_bundled():
    for name in ("RWStore.properties", "RWStore.conformance.properties"):
        assert (DATA_DIR / name).is_file(), f"missing package data: {name}"


def test_conformance_template_enables_quads():
    default = (DATA_DIR / "RWStore.properties").read_text()
    conformance = (DATA_DIR / "RWStore.conformance.properties").read_text()
    assert "com.bigdata.rdf.store.AbstractTripleStore.quads=false" in default
    assert (
        "com.bigdata.rdf.store.AbstractTripleStore.quads=true" in conformance
    )


def test_ensure_rwstore_properties_copies_template_to_cwd(
    tmp_path, monkeypatch
):
    pytest.importorskip("qblazegraph")
    from sparql_conformance.engines.blazegraph_manager import (
        BlazegraphManager,
    )

    monkeypatch.chdir(tmp_path)
    BlazegraphManager()._ensure_rwstore_properties(graph_paths=())
    copied = tmp_path / "RWStore.properties"
    assert copied.is_file()
    # _requires_quads_mode is currently always true, so the conformance
    # (quads=true) template must be the one that lands in the cwd.
    assert (
        "com.bigdata.rdf.store.AbstractTripleStore.quads=true"
        in copied.read_text()
    )
