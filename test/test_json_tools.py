"""Golden tests for the SPARQL JSON results (srj) comparator."""

import json

from sparql_conformance.json_tools import compare_json
from sparql_conformance.test_object import ErrorMessage, Status

XSD = "http://www.w3.org/2001/XMLSchema#"

NUMBER_TYPES = [
    XSD + "integer",
    XSD + "double",
    XSD + "decimal",
    XSD + "float",
    XSD + "int",
    XSD + "decimal",
]

INT_ALIAS = [(XSD + "int", XSD + "integer")]


def srj(rows, variables=("s",)):
    return json.dumps({
        "head": {"vars": list(variables)},
        "results": {"bindings": rows},
    })


def srj_boolean(value):
    return json.dumps({"head": {}, "boolean": value})


def lit(value, datatype=None):
    binding = {"type": "literal", "value": value}
    if datatype:
        binding["datatype"] = datatype
    return binding


def uri(value):
    return {"type": "uri", "value": value}


def bnode(label):
    return {"type": "bnode", "value": label}


def test_identical_results_pass():
    doc = srj([{"s": uri("http://example.org/a")}])
    status, error, *_ = compare_json(doc, doc, [], NUMBER_TYPES)
    assert status == Status.PASSED
    assert error == ""


def test_row_order_is_ignored():
    a = srj([{"s": lit("x")}, {"s": lit("y")}])
    b = srj([{"s": lit("y")}, {"s": lit("x")}])
    status, *_ = compare_json(a, b, [], NUMBER_TYPES)
    assert status == Status.PASSED


def test_blank_node_labels_are_ignored():
    a = srj([{"s": bnode("b1")}, {"s": bnode("b2")}])
    b = srj([{"s": bnode("x")}, {"s": bnode("y")}])
    status, *_ = compare_json(a, b, [], NUMBER_TYPES)
    assert status == Status.PASSED


def test_different_values_fail():
    a = srj([{"s": lit("x")}])
    b = srj([{"s": lit("z")}])
    status, error, *_ = compare_json(a, b, [], NUMBER_TYPES)
    assert status == Status.FAILED
    assert error == ErrorMessage.RESULTS_NOT_THE_SAME


def test_missing_row_fails():
    a = srj([{"s": lit("x")}, {"s": lit("y")}])
    b = srj([{"s": lit("x")}])
    status, *_ = compare_json(a, b, [], NUMBER_TYPES)
    assert status == Status.FAILED


def test_datatype_alias_is_intended_deviation():
    a = srj([{"s": lit("42", XSD + "integer")}])
    b = srj([{"s": lit("42", XSD + "int")}])
    status, error, *_ = compare_json(a, b, INT_ALIAS, NUMBER_TYPES)
    assert status == Status.INTENDED
    assert error == ErrorMessage.INTENDED_MSG


def test_datatype_mismatch_without_alias_fails():
    a = srj([{"s": lit("42", XSD + "integer")}])
    b = srj([{"s": lit("42", XSD + "int")}])
    status, *_ = compare_json(a, b, [], NUMBER_TYPES)
    assert status == Status.FAILED


def test_numeric_lexical_variants_are_equal():
    a = srj([{"s": lit("1.0", XSD + "double")}])
    b = srj([{"s": lit("1", XSD + "double")}])
    status, *_ = compare_json(a, b, [], NUMBER_TYPES)
    assert status == Status.PASSED


def test_boolean_results():
    assert compare_json(
        srj_boolean(True), srj_boolean(True), [], NUMBER_TYPES
    )[0] == Status.PASSED
    assert compare_json(
        srj_boolean(True), srj_boolean(False), [], NUMBER_TYPES
    )[0] == Status.FAILED


def test_empty_results_pass():
    a = srj([], variables=())
    status, *_ = compare_json(a, a, [], NUMBER_TYPES)
    assert status == Status.PASSED
