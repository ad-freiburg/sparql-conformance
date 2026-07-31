"""Golden tests for the Turtle graph comparator."""

from sparql_conformance.rdf_tools import compare_ttl
from sparql_conformance.test_object import ErrorMessage, Status


def test_identical_graphs_pass():
    doc = "<http://e.org/s> <http://e.org/p> <http://e.org/o> .\n"
    status, error, *_ = compare_ttl(doc, doc)
    assert status == Status.PASSED
    assert error == ""


def test_triple_order_is_ignored():
    a = ("<http://e.org/s> <http://e.org/p> \"1\" .\n"
         "<http://e.org/s> <http://e.org/p> \"2\" .\n")
    b = ("<http://e.org/s> <http://e.org/p> \"2\" .\n"
         "<http://e.org/s> <http://e.org/p> \"1\" .\n")
    status, *_ = compare_ttl(a, b)
    assert status == Status.PASSED


def test_blank_node_isomorphism():
    a = "_:a <http://e.org/p> _:b .\n"
    b = "_:x <http://e.org/p> _:y .\n"
    status, *_ = compare_ttl(a, b)
    assert status == Status.PASSED


def test_different_graphs_fail():
    a = "<http://e.org/s> <http://e.org/p> \"1\" .\n"
    b = "<http://e.org/s> <http://e.org/p> \"2\" .\n"
    status, error, *_ = compare_ttl(a, b)
    assert status == Status.FAILED
    assert error == ErrorMessage.RESULTS_NOT_THE_SAME


def test_unparsable_actual_is_format_error():
    a = "<http://e.org/s> <http://e.org/p> \"1\" .\n"
    status, error, *_ = compare_ttl(a, "this is (not turtle")
    assert status == Status.FAILED
    assert error == ErrorMessage.FORMAT_ERROR


def test_unparsable_expected_is_not_tested():
    b = "<http://e.org/s> <http://e.org/p> \"1\" .\n"
    status, error, *_ = compare_ttl("this is (not turtle", b)
    assert status == Status.NOT_TESTED
    assert error == ErrorMessage.FORMAT_ERROR


def test_known_prefixes_are_recovered():
    # compare_ttl injects foaf/v prefixes when the expected file relies on
    # them without declaring them (some W3C expected results do this).
    a = "_:a foaf:name \"Alice\" .\n"
    b = ("_:x <http://xmlns.com/foaf/0.1/name> \"Alice\" .\n")
    status, *_ = compare_ttl(a, b)
    assert status == Status.PASSED
