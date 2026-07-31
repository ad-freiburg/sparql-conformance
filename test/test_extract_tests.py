"""Tests for manifest parsing and test grouping (extract_tests)."""

from pathlib import Path

import pytest

from sparql_conformance.config import Config
from sparql_conformance.extract_tests import extract_tests

FIXTURE_SUITE = str(Path(__file__).parent / "fixtures" / "mini-suite")


def make_config(include=None, exclude=()):
    return Config(
        image=None,
        system="native",
        port="7001",
        graph_store="sparql",
        testsuite_dir=FIXTURE_SUITE,
        type_alias=[],
        binaries_directory="",
        exclude=list(exclude),
        include=include,
    )


@pytest.fixture()
def suite():
    return extract_tests(make_config())


def all_tests(graph_index):
    return [
        test
        for groups in graph_index.values()
        for tests in groups.values()
        for test in tests
    ]


def test_total_count(suite):
    _, count = suite
    assert count == 8


def test_category_grouping(suite):
    graph_index, _ = suite
    by_category = {
        category: [t.name for group in groups.values() for t in group]
        for category, groups in graph_index.items()
    }
    assert sorted(by_category["query"]) == [
        "ask-true", "construct-basic", "select-basic", "select-int",
    ]
    assert sorted(by_category["syntax"]) == ["syntax-bad", "syntax-good"]
    assert by_category["update"] == ["update-insert"]
    assert by_category["service"] == ["service-description"]
    assert by_category["protocol"] == []
    assert by_category["federation"] == []


def test_query_tests_share_one_graph_group(suite):
    graph_index, _ = suite
    # All four query tests use data.ttl, so they must be in a single group
    # (one index build for all of them).
    assert len(graph_index["query"]) == 1
    (graph_key,) = graph_index["query"].keys()
    assert graph_key[0][0].endswith("data.ttl")


def test_file_contents_are_loaded(suite):
    graph_index, _ = suite
    by_name = {t.name: t for t in all_tests(graph_index)}

    select_basic = by_name["select-basic"]
    assert "SELECT ?o" in select_basic.query_file
    assert select_basic.result_format == "ttl"
    assert "rs:ResultSet" in select_basic.result_file
    assert select_basic.group == "mini-suite"

    assert by_name["select-int"].result_format == "srj"
    assert by_name["construct-basic"].result_format == "ttl"

    update = by_name["update-insert"]
    assert "INSERT DATA" in update.query_file
    assert "ex:new" in update.result_file


def test_syntax_tests_fall_back_to_empty_graph(suite):
    graph_index, _ = suite
    (graph_key,) = graph_index["syntax"].keys()
    assert graph_key[0][0].endswith("empty.ttl")


def test_include_filter():
    graph_index, count = extract_tests(make_config(include=["select-basic"]))
    assert count == 1
    assert all_tests(graph_index)[0].name == "select-basic"


def test_exclude_filter():
    _, count = extract_tests(make_config(exclude=["syntax-bad"]))
    assert count == 7


def test_group_filter_matches_directory_name():
    _, count = extract_tests(make_config(include=["mini-suite"]))
    assert count == 8
