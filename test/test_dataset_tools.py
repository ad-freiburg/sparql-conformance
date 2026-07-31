"""Tests for resolving and staging query-declared datasets."""

import html
from pathlib import Path

import pytest

from sparql_conformance.config import Config
from sparql_conformance.dataset_tools import prepare_query_dataset
from sparql_conformance.engines.rdflib_manager import RdflibEngineManager
from sparql_conformance.extract_tests import collect_tests_by_graph
from sparql_conformance.test_object import ErrorMessage, Status, TestObject
from sparql_conformance.testsuite import TestSuite


def write_data(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "@prefix ex: <http://example.org/> . ex:s ex:p ex:o .\n"
    )
    return path


def prepare(tmp_path: Path, query: str):
    query_path = tmp_path / "query.rq"
    query_path.write_text(query)
    return prepare_query_dataset(query, str(query_path))


def make_config(tmp_path):
    return Config(
        image=None,
        system="native",
        port="7001",
        graph_store="sparql",
        testsuite_dir=str(tmp_path),
        type_alias=[],
        binaries_directory="",
        exclude=[],
        include=None,
    )


def make_test_object(tmp_path, query):
    query_path = tmp_path / "query.rq"
    query_path.write_text(query)
    result_path = tmp_path / "result.ttl"
    result_path.write_text(
        """@prefix rs: <http://www.w3.org/2001/sw/DataAccess/tests/result-set#> .
        [] a rs:ResultSet ; rs:resultVariable "s" ."""
    )
    return TestObject(
        test="urn:test",
        name="dataset-test",
        type_name="QueryEvaluationTest",
        group="fixture",
        path=str(tmp_path) + "/",
        action_node={"query": str(query_path)},
        result_node={"data": str(result_path)},
        approval=None,
        approved_by=None,
        comment=None,
        entailment_regime=None,
        entailment_profile=None,
        feature=[],
        config=make_config(tmp_path),
    )


def test_single_from_uses_query_file_as_implicit_base(tmp_path):
    data = write_data(tmp_path / "data.ttl")
    original = "SELECT * FROM <data.ttl> WHERE { ?s ?p ?o }\n"
    prepared = prepare(
        tmp_path,
        original,
    )

    assert prepared.setup_error == ""
    assert prepared.sources[0].local_path == str(data)
    assert prepared.sources[0].graph_iri == data.as_uri()
    assert prepared.query == (
        f"BASE <{tmp_path.as_uri()}/>\n{original}"
    )


def test_multiple_mixed_dataset_clauses_are_all_staged_as_named_graphs(
    tmp_path,
):
    first = write_data(tmp_path / "first.ttl")
    second = write_data(tmp_path / "second.ttl")
    prepared = prepare(
        tmp_path,
        """SELECT * FROM <first.ttl>
        FROM NAMED <second.ttl>
        WHERE { ?s ?p ?o }""",
    )

    assert prepared.setup_error == ""
    assert [(source.local_path, source.graph_iri) for source in prepared.sources] == [
        (str(first), first.as_uri()),
        (str(second), second.as_uri()),
    ]
    assert "FROM <first.ttl>" in prepared.query
    assert "FROM NAMED <second.ttl>" in prepared.query


def test_explicit_base_is_resolved_by_rdflib(tmp_path):
    data = write_data(tmp_path / "sub" / "data.ttl")
    query = f"""BASE <{(tmp_path / "sub").as_uri() + "/"}>
        SELECT * FROM <data.ttl> WHERE {{ ?s ?p ?o }}"""
    prepared = prepare(
        tmp_path,
        query,
    )

    assert prepared.setup_error == ""
    assert prepared.sources[0].graph_iri == data.as_uri()
    assert prepared.query == query


def test_prefixed_dataset_iri_is_resolved_without_rewriting(tmp_path):
    data = write_data(tmp_path / "data.ttl")
    query = """PREFIX files: <./>
        SELECT * FROM files:data.ttl WHERE { ?s ?p ?o }"""
    prepared = prepare(
        tmp_path,
        query,
    )

    assert prepared.setup_error == ""
    assert prepared.sources[0].graph_iri == data.as_uri()
    assert prepared.query.endswith(query)
    assert "FROM files:data.ttl" in prepared.query


def test_comments_and_strings_containing_from_are_untouched(tmp_path):
    data = write_data(tmp_path / "data.ttl")
    query = """# FROM <ignored.ttl>
    SELECT ("FROM <also-ignored.ttl>" AS ?text)
    FROM <data.ttl>
    WHERE { ?s ?p ?o }"""
    prepared = prepare(tmp_path, query)

    assert prepared.setup_error == ""
    assert len(prepared.sources) == 1
    assert "# FROM <ignored.ttl>" in prepared.query
    assert '"FROM <also-ignored.ttl>"' in prepared.query
    assert "FROM <data.ttl>" in prepared.query


def test_duplicate_dataset_sources_are_staged_once(tmp_path):
    data = write_data(tmp_path / "data.ttl")
    prepared = prepare(
        tmp_path,
        """SELECT * FROM <data.ttl> FROM NAMED <data.ttl>
        WHERE { ?s ?p ?o }""",
    )

    assert prepared.setup_error == ""
    assert len(prepared.sources) == 1
    assert prepared.query.count("<data.ttl>") == 2


def test_query_without_dataset_clauses_gets_implicit_base(tmp_path):
    query = """# FROM <ignored.ttl>
    SELECT ("FROM <also-ignored.ttl>" AS ?text)
    WHERE { ?s ?p ?o }"""

    prepared = prepare(tmp_path, query)

    assert prepared.setup_error == ""
    assert prepared.sources == ()
    assert prepared.query == f"BASE <{tmp_path.as_uri()}/>\n{query}"


def test_query_without_dataset_does_not_require_algebra_translation(
    tmp_path,
    monkeypatch,
):
    query = """SELECT ?s WHERE {
        SERVICE <http://example.org/sparql> { ?s ?p ?o }
    }"""

    def translation_must_not_run(*args, **kwargs):
        raise AssertionError("algebra translation must not run")

    monkeypatch.setattr(
        "sparql_conformance.dataset_tools.translateQuery",
        translation_must_not_run,
    )

    prepared = prepare(tmp_path, query)

    assert prepared.setup_error == ""
    assert prepared.sources == ()
    assert prepared.query == f"BASE <{tmp_path.as_uri()}/>\n{query}"


def test_explicit_base_without_dataset_is_preserved(tmp_path):
    query = "BASE <http://example.org/> SELECT * WHERE { ?s ?p ?o }"

    prepared = prepare(tmp_path, query)

    assert prepared.setup_error == ""
    assert prepared.sources == ()
    assert prepared.query == query


def test_absolute_file_source_is_staged(tmp_path):
    data = write_data(tmp_path / "data.ttl")
    prepared = prepare(
        tmp_path,
        f"SELECT * FROM <{data.as_uri()}> WHERE {{ ?s ?p ?o }}",
    )
    assert prepared.setup_error == ""
    assert prepared.sources[0].local_path == str(data)


def test_result_json_preserves_original_query_and_reports_execution_metadata(
    tmp_path,
):
    data = write_data(tmp_path / "data.ttl")
    original = "SELECT * FROM <data.ttl> WHERE { ?s ?p ?o }"
    test = make_test_object(tmp_path, original)
    result = test.to_dict()

    assert html.unescape(result["queryFile"]) == original
    execution_query = html.unescape(result["executionQuery"])
    assert execution_query.startswith(
        f"BASE <{tmp_path.as_uri()}/>\n"
    )
    assert execution_query.endswith(original)
    assert result["datasetSources"] == [{
        "localPath": str(data),
        "graphIri": data.as_uri(),
    }]


def test_missing_local_source_is_a_setup_error(tmp_path):
    prepared = prepare(
        tmp_path,
        "SELECT * FROM <missing.ttl> WHERE { ?s ?p ?o }",
    )
    assert prepared.sources == ()
    assert "does not exist" in prepared.setup_error


def test_setup_error_is_not_tested_without_starting_engine(tmp_path):
    class EngineThatMustNotStart(RdflibEngineManager):
        def setup(self, config, graph_paths):
            raise AssertionError("engine setup must not be called")

    test = make_test_object(
        tmp_path,
        "SELECT * FROM <missing.ttl> WHERE { ?s ?p ?o }",
    )
    tests = collect_tests_by_graph([test])
    suite = TestSuite(
        name="setup-error",
        tests=tests,
        test_count=1,
        config=make_config(tmp_path),
        engine_manager=EngineThatMustNotStart(),
        results_dir=str(tmp_path),
    )
    suite.run()

    assert test.status == Status.NOT_TESTED
    assert test.error_type == ErrorMessage.TEST_SETUP_ERROR
    assert "does not exist" in test.query_log


@pytest.mark.parametrize(
    "iri",
    [
        "https://example.org/data.ttl",
        "urn:example:data",
    ],
)
def test_remote_or_non_file_sources_are_not_fetched(tmp_path, iri):
    prepared = prepare(
        tmp_path,
        f"SELECT * FROM <{iri}> WHERE {{ ?s ?p ?o }}",
    )
    assert prepared.sources == ()
    assert "automatic fetching is disabled" in prepared.setup_error
