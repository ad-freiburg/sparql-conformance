"""Regression tests for fixed bugs: server-log capture, explicit
ServiceDescriptionTest skipping, and graph-count mismatches in updates."""

from pathlib import Path

import pytest

from sparql_conformance.config import Config
from sparql_conformance.engines.rdflib_manager import RdflibEngineManager
from sparql_conformance.extract_tests import extract_tests
from sparql_conformance.test_object import ErrorMessage, Status
from sparql_conformance.testsuite import TestSuite

FIXTURE_SUITE = str(Path(__file__).parent / "fixtures" / "mini-suite")


class LoggingRdflibManager(RdflibEngineManager):
    """Reference engine that also produces a server log, like the real
    engine managers do."""

    def get_server_log(self, config):
        return "ENGINE LOG LINE"


def make_config(graph_store="sparql"):
    return Config(
        image=None,
        system="native",
        port="7001",
        graph_store=graph_store,
        testsuite_dir=FIXTURE_SUITE,
        type_alias=[],
        binaries_directory="",
        exclude=[],
        include=None,
    )


def make_suite(engine_manager):
    config = make_config()
    tests, test_count = extract_tests(config)
    return TestSuite(
        name="regression",
        tests=tests,
        test_count=test_count,
        config=config,
        engine_manager=engine_manager,
        results_dir=".",
        report_mode="none",
    )


class CustomGraphStoreManager(RdflibEngineManager):
    def graph_store_endpoint(self):
        return "engine-default-graph-store"


def test_engine_manager_supplies_graph_store_default():
    config = make_config(graph_store=None)

    TestSuite(
        name="graph-store-default",
        tests={},
        test_count=0,
        config=config,
        engine_manager=CustomGraphStoreManager(),
    )

    assert config.GRAPHSTORE == "engine-default-graph-store"


def test_explicit_graph_store_override_is_preserved():
    config = make_config(graph_store="custom-override")

    TestSuite(
        name="graph-store-override",
        tests={},
        test_count=0,
        config=config,
        engine_manager=CustomGraphStoreManager(),
    )

    assert config.GRAPHSTORE == "custom-override"


def test_default_get_server_log_reads_run_id_file(tmp_path, monkeypatch):
    # Bug: the suite used to read a fixed ./TestSuite.server-log.txt, which
    # no engine manager ever wrote; server logs silently never reached the
    # results. The managers write ./<run_id>.server-log.txt.
    monkeypatch.chdir(tmp_path)
    config = make_config()
    (tmp_path / f"{config.run_id}.server-log.txt").write_text("the log")
    assert RdflibEngineManager().get_server_log(config) == "the log"


def test_get_server_log_returns_empty_when_missing(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert RdflibEngineManager().get_server_log(make_config()) == ""


def test_server_log_is_attached_to_test_results(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    suite = make_suite(LoggingRdflibManager())
    suite.run()
    tests_dict, _ = suite.build_results_dict()
    assert "ENGINE LOG LINE" in tests_dict["select-basic"]["serverLog"]


def test_service_description_tests_are_explicitly_skipped(
    tmp_path, monkeypatch
):
    # Bug: ServiceDescriptionTests were collected but never touched by
    # run(); they kept their initial state with no explanation.
    monkeypatch.chdir(tmp_path)
    suite = make_suite(RdflibEngineManager())
    suite.run()
    tests_dict, _ = suite.build_results_dict()
    entry = tests_dict["service-description"]
    assert entry["status"] == Status.NOT_TESTED
    assert entry["errorType"] == ErrorMessage.NOT_TESTED
    assert "not supported" in entry["queryLog"]


def test_update_graph_count_mismatch_fails_test_not_run(tmp_path, monkeypatch):
    # Bug: evaluate_update asserted len(expected) == len(actual), so one
    # malformed test aborted the entire suite run (and the check vanished
    # under python -O).
    monkeypatch.chdir(tmp_path)
    suite = make_suite(RdflibEngineManager())
    update_groups = suite.tests["update"]
    (test,) = [t for group in update_groups.values() for t in group]

    suite.evaluate_update(["g1", "g2"], ["g1"], test)

    assert test.status == Status.FAILED
    assert test.error_type == ErrorMessage.RESULTS_NOT_THE_SAME
    assert "Mismatched graph counts" in test.query_log


def test_malformed_xml_for_legacy_turtle_result_is_a_format_error():
    suite = make_suite(RdflibEngineManager())
    test = next(
        test
        for group in suite.tests["query"].values()
        for test in group
        if test.name == "select-basic"
    )

    suite.evaluate_query(
        test.result_file,
        "<not-finished>",
        test,
        result_format="ttl",
        response_format="srx",
    )

    assert test.status == Status.FAILED
    assert test.error_type == ErrorMessage.FORMAT_ERROR
    assert "<not-finished>" in test.query_log
