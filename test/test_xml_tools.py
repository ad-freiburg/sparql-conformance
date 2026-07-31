"""Golden tests for the SPARQL XML results (srx) comparator."""

from sparql_conformance.test_object import ErrorMessage, Status
from sparql_conformance.xml_tools import compare_xml

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


def srx(rows, variables=("s",)):
    """Build a SPARQL XML results document from a list of rows, each row a
    dict mapping variable name to a binding XML fragment."""
    head = "".join(f'<variable name="{v}"/>' for v in variables)
    results = ""
    for row in rows:
        bindings = "".join(
            f'<binding name="{var}">{fragment}</binding>'
            for var, fragment in row.items()
        )
        results += f"<result>{bindings}</result>"
    return (
        '<?xml version="1.0"?>\n'
        '<sparql xmlns="http://www.w3.org/2005/sparql-results#">'
        f"<head>{head}</head><results>{results}</results></sparql>"
    )


def srx_boolean(value):
    return (
        '<?xml version="1.0"?>\n'
        '<sparql xmlns="http://www.w3.org/2005/sparql-results#">'
        f"<head/><boolean>{value}</boolean></sparql>"
    )


def lit(value, datatype=None):
    if datatype:
        return f'<literal datatype="{datatype}">{value}</literal>'
    return f"<literal>{value}</literal>"


def uri(value):
    return f"<uri>{value}</uri>"


def bnode(label):
    return f"<bnode>{label}</bnode>"


def test_identical_results_pass():
    doc = srx([{"s": uri("http://example.org/a")}])
    status, error, *_ = compare_xml(doc, doc, [], NUMBER_TYPES)
    assert status == Status.PASSED
    assert error == ""


def test_row_order_is_ignored():
    a = srx([{"s": lit("x")}, {"s": lit("y")}])
    b = srx([{"s": lit("y")}, {"s": lit("x")}])
    status, *_ = compare_xml(a, b, [], NUMBER_TYPES)
    assert status == Status.PASSED


def test_blank_node_labels_are_ignored():
    a = srx([{"s": bnode("b1")}, {"s": bnode("b2")}])
    b = srx([{"s": bnode("x")}, {"s": bnode("y")}])
    status, *_ = compare_xml(a, b, [], NUMBER_TYPES)
    assert status == Status.PASSED


def test_different_values_fail():
    a = srx([{"s": lit("x")}])
    b = srx([{"s": lit("z")}])
    status, error, *_ = compare_xml(a, b, [], NUMBER_TYPES)
    assert status == Status.FAILED
    assert error == ErrorMessage.RESULTS_NOT_THE_SAME


def test_missing_row_fails():
    a = srx([{"s": lit("x")}, {"s": lit("y")}])
    b = srx([{"s": lit("x")}])
    status, *_ = compare_xml(a, b, [], NUMBER_TYPES)
    assert status == Status.FAILED


def test_datatype_alias_is_intended_deviation():
    a = srx([{"s": lit("42", XSD + "integer")}])
    b = srx([{"s": lit("42", XSD + "int")}])
    status, error, *_ = compare_xml(a, b, INT_ALIAS, NUMBER_TYPES)
    assert status == Status.INTENDED
    assert error == ErrorMessage.INTENDED_MSG


def test_datatype_mismatch_without_alias_fails():
    a = srx([{"s": lit("42", XSD + "integer")}])
    b = srx([{"s": lit("42", XSD + "int")}])
    status, *_ = compare_xml(a, b, [], NUMBER_TYPES)
    assert status == Status.FAILED


def test_numeric_lexical_variants_are_equal():
    a = srx([{"s": lit("1.0", XSD + "double")}])
    b = srx([{"s": lit("1", XSD + "double")}])
    status, *_ = compare_xml(a, b, [], NUMBER_TYPES)
    assert status == Status.PASSED


def test_boolean_results():
    assert compare_xml(
        srx_boolean("true"), srx_boolean("true"), [], NUMBER_TYPES
    )[0] == Status.PASSED
    assert compare_xml(
        srx_boolean("true"), srx_boolean("false"), [], NUMBER_TYPES
    )[0] == Status.FAILED


def test_malformed_result_is_format_error():
    a = srx([{"s": lit("x")}])
    status, error, *_ = compare_xml(a, "this is not xml", [], NUMBER_TYPES)
    assert status == Status.FAILED
    assert error == ErrorMessage.FORMAT_ERROR


def test_empty_results_pass():
    a = srx([], variables=())
    status, *_ = compare_xml(a, a, [], NUMBER_TYPES)
    assert status == Status.PASSED
