"""End-to-end smoke test: manifest -> TestSuite.run() -> v2 results dict,
using the in-process rdflib reference engine (no docker, no binaries)."""

import bz2
import json
from pathlib import Path

import pytest

from sparql_conformance.config import Config
from sparql_conformance.engines.rdflib_manager import RdflibEngineManager
from sparql_conformance.extract_tests import extract_tests
from sparql_conformance.test_object import Status
from sparql_conformance.testsuite import TestSuite

FIXTURE_SUITE = str(Path(__file__).parent / "fixtures" / "mini-suite")


class RecordingRdflibManager(RdflibEngineManager):
    def __init__(self):
        super().__init__()
        self.query_formats = []

    def query(self, config, query, result_format):
        self.query_formats.append((query, result_format))
        return super().query(config, query, result_format)


@pytest.fixture()
def run_results(tmp_path, monkeypatch):
    # The suite writes engine work files and reads server logs from the
    # current directory.
    monkeypatch.chdir(tmp_path)
    config = Config(
        image=None,
        system="native",
        port="7001",
        graph_store="sparql",
        testsuite_dir=FIXTURE_SUITE,
        type_alias=[],
        binaries_directory="",
        exclude=[],
        include=None,
    )
    tests, test_count = extract_tests(config)
    suite = TestSuite(
        name="e2e",
        tests=tests,
        test_count=test_count,
        config=config,
        engine_manager=RecordingRdflibManager(),
        results_dir=str(tmp_path),
        report_mode="none",
    )
    suite.run()
    return suite


def statuses_by_name(suite):
    tests_dict, info = suite.build_results_dict()
    return {t["name"]: t["status"] for t in tests_dict.values()}, info


def test_all_supported_tests_pass(run_results):
    statuses, _ = statuses_by_name(run_results)
    expected_passed = [
        "select-basic", "select-int", "ask-true", "construct-basic",
        "syntax-good", "syntax-bad", "update-insert",
    ]
    for name in expected_passed:
        assert statuses[name] == Status.PASSED, (
            f"{name}: {statuses[name]}"
        )


def test_legacy_turtle_result_sets_are_requested_as_xml(run_results):
    query_formats = run_results.engine_manager.query_formats
    assert next(
        result_format
        for query, result_format in query_formats
        if "SELECT ?o WHERE" in query
    ) == "srx"
    assert next(
        result_format
        for query, result_format in query_formats
        if "ASK {" in query
    ) == "srx"
    assert next(
        result_format
        for query, result_format in query_formats
        if "SELECT ?o WHERE { <http://example.org/s2>" in query
    ) == "srj"
    assert next(
        result_format
        for query, result_format in query_formats
        if "CONSTRUCT { ?s" in query
    ) == "ttl"


def test_service_description_is_not_silently_counted_as_run(run_results):
    statuses, _ = statuses_by_name(run_results)
    assert statuses["service-description"] == Status.NOT_TESTED


def test_info_totals(run_results):
    _, info = statuses_by_name(run_results)
    assert info["tests"] == 8
    assert info["passed"] == 7
    assert info["failed"] == 0
    assert info["notTested"] == 1


def test_result_file_is_valid_v2_json(run_results, tmp_path):
    tests_dict, info = run_results.build_results_dict()
    output = {
        "version": 2,
        "suites": {"mini": {"tests": tests_dict, "info": info}},
        "info": {"name": "info", **info},
    }
    out_file = tmp_path / "e2e.json.bz2"
    run_results.compress_json_bz2(output, str(out_file))
    with bz2.open(out_file, "rt") as f:
        loaded = json.load(f)
    assert loaded["version"] == 2
    assert loaded["suites"]["mini"]["info"]["tests"] == 8
    # Every test entry carries the fields the web UI relies on.
    for entry in loaded["suites"]["mini"]["tests"].values():
        for field in (
            "name",
            "status",
            "typeName",
            "group",
            "errorType",
            "executionQuery",
            "datasetSources",
        ):
            assert field in entry


def test_relative_graph_data_uses_its_resolved_file_iri(tmp_path, monkeypatch):
    suite_dir = tmp_path / "suite"
    suite_dir.mkdir()
    graph_file = suite_dir / "named.ttl"
    graph_file.write_text(
        "<http://example.org/s> <http://example.org/p> "
        "<http://example.org/o> .\n",
        encoding="utf-8",
    )
    (suite_dir / "query.rq").write_text(
        "SELECT (<named.ttl> AS ?g) WHERE { GRAPH <named.ttl> { "
        "<http://example.org/s> <http://example.org/p> "
        "<http://example.org/o> } }\n",
        encoding="utf-8",
    )
    (suite_dir / "result.ttl").write_text(
        """@prefix rs: <http://www.w3.org/2001/sw/DataAccess/tests/result-set#> .
        [] a rs:ResultSet ;
           rs:resultVariable "g" ;
           rs:solution [ rs:binding [
             rs:variable "g" ; rs:value <named.ttl>
           ] ] .
        """,
        encoding="utf-8",
    )
    (suite_dir / "manifest.ttl").write_text(
        """@prefix mf: <http://www.w3.org/2001/sw/DataAccess/tests/test-manifest#> .
        @prefix qt: <http://www.w3.org/2001/sw/DataAccess/tests/test-query#> .
        @prefix : <manifest#> .
        <> a mf:Manifest ; mf:entries ( :graph-iri ) .
        :graph-iri a mf:QueryEvaluationTest ;
            mf:name "graph-iri" ;
            mf:action [ qt:query <query.rq> ; qt:graphData <named.ttl> ] ;
            mf:result <result.ttl> .
        """,
        encoding="utf-8",
    )

    work_dir = tmp_path / "work"
    work_dir.mkdir()
    monkeypatch.chdir(work_dir)
    config = Config(
        image=None,
        system="native",
        port="7001",
        graph_store="sparql",
        testsuite_dir=str(suite_dir),
        type_alias=[],
        binaries_directory="",
        exclude=[],
        include=None,
    )
    tests, test_count = extract_tests(config)
    graph_iri = graph_file.resolve().as_uri()
    (graph_group,) = tests["query"].keys()
    assert (str(graph_file.resolve()), graph_iri) in graph_group

    suite = TestSuite(
        name="graph-iri",
        tests=tests,
        test_count=test_count,
        config=config,
        engine_manager=RdflibEngineManager(),
        results_dir=str(work_dir),
        report_mode="none",
    )
    suite.run()
    statuses, _ = statuses_by_name(suite)
    assert statuses["graph-iri"] == Status.PASSED
