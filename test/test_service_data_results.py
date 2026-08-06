"""Tests for SERVICE endpoint fixture execution and result metadata."""

import json
from pathlib import Path

import pytest

from sparql_conformance.config import Config
from sparql_conformance.test_object import ErrorMessage, Status, TestObject
from sparql_conformance.testsuite import TestSuite


def make_config(tmp_path: Path) -> Config:
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


def make_test(tmp_path: Path, service_data=None) -> TestObject:
    query_path = tmp_path / "query.rq"
    query_path.write_text(
        "SELECT * WHERE { SERVICE <http://example.org/sparql> { ?s ?p ?o } }\n",
        encoding="utf-8",
    )
    result_path = tmp_path / "result.srj"
    result_path.write_text(
        '{"head": {"vars": []}, "results": {"bindings": []}}',
        encoding="utf-8",
    )
    action = {"query": str(query_path)}
    if service_data is not None:
        action["serviceData"] = service_data
    return TestObject(
        test="urn:test",
        name="service-test",
        type_name="QueryEvaluationTest",
        group="service",
        path=str(tmp_path),
        action_node=action,
        result_node={"data": str(result_path)},
        approval=None,
        approved_by=None,
        comment=None,
        entailment_regime=None,
        entailment_profile=None,
        feature=[],
        config=make_config(tmp_path),
    )


def test_single_fixture_is_normalized_and_serialized_without_source_path(tmp_path):
    fixture_path = tmp_path / "endpoint.ttl"
    content = "@prefix ex: <http://example.org/> .\nex:s ex:p ex:o .\n"
    fixture_path.write_text(content, encoding="utf-8")
    test = make_test(tmp_path, {
        "endpoint": "http://example.org/sparql",
        "data": str(fixture_path),
    })

    assert len(test.service_data_fixtures) == 1
    result = test.to_dict()
    assert result["serviceData"] == [{
        "endpoint": "http://example.org/sparql",
        "fileName": "endpoint.ttl",
        "content": content,
    }]
    assert str(tmp_path) not in json.dumps(result["serviceData"])


def test_multiple_fixtures_preserve_manifest_order_and_empty_content(tmp_path):
    first = tmp_path / "first.ttl"
    second = tmp_path / "second.ttl"
    first.write_text("first\n", encoding="utf-8")
    second.write_text("", encoding="utf-8")
    test = make_test(tmp_path, [
        {"endpoint": "http://first.example/sparql", "data": str(first)},
        {"endpoint": "http://second.example/sparql", "data": str(second)},
    ])

    assert [fixture.endpoint for fixture in test.service_data_fixtures] == [
        "http://first.example/sparql",
        "http://second.example/sparql",
    ]
    assert [fixture.content for fixture in test.service_data_fixtures] == [
        "first\n",
        "",
    ]


def test_non_service_test_serializes_empty_fixture_array(tmp_path):
    assert make_test(tmp_path).to_dict()["serviceData"] == []


@pytest.mark.parametrize(
    ("service_data", "message"),
    [
        ({"data": "fixture.ttl"}, "missing a non-empty endpoint"),
        ({"endpoint": "http://example.org/sparql"}, "missing a non-empty data path"),
        (
            {"endpoint": "http://example.org/sparql", "data": "missing.ttl"},
            "data file is unreadable: missing.ttl",
        ),
    ],
)
def test_malformed_fixture_produces_setup_error(tmp_path, service_data, message):
    test = make_test(tmp_path, service_data)

    assert message in test.setup_error


def test_unreadable_fixture_produces_setup_error(tmp_path):
    directory = tmp_path / "fixture.ttl"
    directory.mkdir()
    test = make_test(tmp_path, {
        "endpoint": "http://example.org/sparql",
        "data": str(directory),
    })

    assert "SERVICE fixture 1 data file is unreadable" in test.setup_error


def test_setup_error_skips_federation_execution(tmp_path):
    class EngineThatMustNotRun:
        def query(self, config, query, result_format):
            raise AssertionError("query must not run")

    test = make_test(tmp_path, {
        "endpoint": "http://example.org/sparql",
        "data": "missing.ttl",
    })
    suite = TestSuite(
        name="service-error",
        tests={"federation": {((),): [test]}},
        test_count=1,
        config=make_config(tmp_path),
        engine_manager=EngineThatMustNotRun(),
        results_dir=str(tmp_path),
    )

    suite.run_federation_tests({(): [test]})

    assert test.status == Status.NOT_TESTED
    assert test.error_type == ErrorMessage.TEST_SETUP_ERROR


def test_federation_execution_uses_the_serialized_fixture_content(
        tmp_path,
        monkeypatch,
):
    fixture_path = tmp_path / "endpoint.ttl"
    content = "<urn:s> <urn:p> <urn:o> .\n"
    fixture_path.write_text(content, encoding="utf-8")
    test = make_test(tmp_path, {
        "endpoint": "http://example.org/sparql",
        "data": str(fixture_path),
    })
    recorded_endpoints = []

    class FakeMockServer:
        def add_endpoint(self, endpoint, fixture_content):
            recorded_endpoints.append((endpoint, fixture_content))

        def start(self):
            pass

        def stop(self):
            pass

        def local_url_for(self, endpoint, host):
            assert endpoint == "http://example.org/sparql"
            return f"http://{host}:4321/mock"

    class RecordingEngine:
        def __init__(self):
            self.queries = []

        def query(self, config, query, result_format):
            self.queries.append(query)
            return 500, "expected test response"

        def cleanup(self, config):
            pass

    monkeypatch.setattr(
        "sparql_conformance.testsuite.MockSPARQLServer",
        FakeMockServer,
    )
    engine = RecordingEngine()
    suite = TestSuite(
        name="service",
        tests={"federation": {(): [test]}},
        test_count=1,
        config=make_config(tmp_path),
        engine_manager=engine,
        results_dir=str(tmp_path),
    )
    monkeypatch.setattr(suite, "prepare_test_environment", lambda *args: True)
    monkeypatch.setattr(suite, "refresh_server_log", lambda *args: None)

    suite.run_federation_tests({(): [test]})

    assert recorded_endpoints == [(
        test.to_dict()["serviceData"][0]["endpoint"],
        test.to_dict()["serviceData"][0]["content"],
    )]
    assert "http://127.0.0.1:4321/mock" in engine.queries[0]
    assert test.execution_query == engine.queries[0]
