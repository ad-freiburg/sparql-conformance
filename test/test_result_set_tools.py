"""Tests for semantic comparison of RDF-encoded SPARQL result sets."""

import xml.etree.ElementTree as ET

import pytest
import rdflib

from sparql_conformance.result_set_tools import (
    RESULT_SET,
    RESULT_SET_INDEX,
    compare_rdf_result_set,
    expected_is_result_set,
    is_select_or_ask,
    sparql_xml_to_result_set_ttl,
)
from sparql_conformance.test_object import ErrorMessage, Status


RS = "http://www.w3.org/2001/sw/DataAccess/tests/result-set#"


def select_xml(rows, variables=("value",)):
    head = "".join(f'<variable name="{name}"/>' for name in variables)
    body = "".join(f"<result>{row}</result>" for row in rows)
    return f"""<?xml version="1.0"?>
    <sparql xmlns="http://www.w3.org/2005/sparql-results#">
      <head>{head}</head><results>{body}</results>
    </sparql>"""


def literal_binding(value, name="value", attributes=""):
    return (
        f'<binding name="{name}"><literal {attributes}>'
        f"{value}</literal></binding>"
    )


def bnode_binding(value, name="value"):
    return f'<binding name="{name}"><bnode>{value}</bnode></binding>'


def ordered_result(values):
    solutions = "\n".join(
        f"""rs:solution [
          rs:index {index} ;
          rs:binding [
            rs:variable "value" ;
            rs:value {value}
          ]
        ] ;"""
        for index, value in enumerate(values, start=1)
    )
    return f"""@prefix rs: <{RS}> .
    [] a rs:ResultSet ;
       rs:resultVariable "value" ;
       {solutions}
       .
    """


def test_select_xml_is_converted_with_one_based_indices():
    xml = select_xml([
        literal_binding("first"),
        literal_binding("second"),
    ])
    graph = rdflib.Graph()
    graph.parse(data=sparql_xml_to_result_set_ttl(xml), format="turtle")

    indices = sorted(
        int(value)
        for value in graph.objects(None, RESULT_SET_INDEX)
    )
    assert indices == [1, 2]


def test_unordered_result_preserves_terms_unbound_variables_and_shared_bnodes():
    xml = select_xml(
        [
            (
                '<binding name="uri"><uri>http://example.org/value</uri></binding>'
                '<binding name="typed"><literal datatype="http://www.w3.org/2001/XMLSchema#integer">42</literal></binding>'
                '<binding name="lang"><literal xml:lang="de">hallo</literal></binding>'
                '<binding name="node"><bnode>shared</bnode></binding>'
            ),
            '<binding name="node"><bnode>shared</bnode></binding>',
        ],
        variables=("uri", "typed", "lang", "node", "unbound"),
    )
    expected = f"""@prefix rs: <{RS}> .
    [] a rs:ResultSet ;
       rs:resultVariable "uri", "typed", "lang", "node", "unbound" ;
       rs:solution [
         rs:binding
           [ rs:variable "uri" ; rs:value <http://example.org/value> ],
               [ rs:variable "typed" ; rs:value 42 ],
               [ rs:variable "lang" ; rs:value "hallo"@de ],
               [ rs:variable "node" ; rs:value _:shared ]
       ] ;
       rs:solution [
         rs:binding [
           rs:variable "node" ; rs:value _:shared
         ]
       ] .
    """

    status, *_ = compare_rdf_result_set(expected, xml, "ttl")
    assert status == Status.PASSED


@pytest.mark.parametrize("value", ["true", "false"])
def test_ask_xml_is_converted_to_typed_boolean(value):
    xml = f"""<sparql xmlns="http://www.w3.org/2005/sparql-results#">
      <head/><boolean>{value}</boolean>
    </sparql>"""
    expected = f"""@prefix rs: <{RS}> .
    @prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
    [] a rs:ResultSet ; rs:boolean "{value}"^^xsd:boolean .
    """

    status, *_ = compare_rdf_result_set(expected, xml, "ttl")
    assert status == Status.PASSED


def test_empty_select_result_is_preserved():
    xml = """<sparql xmlns="http://www.w3.org/2005/sparql-results#">
      <head><variable name="x"/></head><results/>
    </sparql>"""
    expected = f"""@prefix rs: <{RS}> .
    [] a rs:ResultSet ; rs:resultVariable "x" .
    """
    status, *_ = compare_rdf_result_set(expected, xml, "ttl")
    assert status == Status.PASSED


def test_rdf_xml_result_set_is_detected_semantically():
    expected = f"""<?xml version="1.0"?>
    <rdf:RDF xmlns:rdf="{rdflib.RDF}" xmlns:rs="{RS}">
      <rs:ResultSet>
        <rs:boolean rdf:datatype="{rdflib.XSD.boolean}">true</rs:boolean>
      </rs:ResultSet>
    </rdf:RDF>"""
    assert expected_is_result_set(expected, "rdf")


def test_rdf_xml_ordered_result_set_is_compared_semantically():
    expected = f"""<?xml version="1.0"?>
    <rdf:RDF xmlns:rdf="{rdflib.RDF}" xmlns:rs="{RS}"
             xmlns:xsd="{rdflib.XSD}">
      <rs:ResultSet>
        <rs:resultVariable>value</rs:resultVariable>
        <rs:solution rdf:parseType="Resource">
          <rs:index rdf:datatype="{rdflib.XSD.integer}">1</rs:index>
          <rs:binding rdf:parseType="Resource">
            <rs:variable>value</rs:variable><rs:value>Alice</rs:value>
          </rs:binding>
        </rs:solution>
        <rs:solution rdf:parseType="Resource">
          <rs:index rdf:datatype="{rdflib.XSD.integer}">2</rs:index>
          <rs:binding rdf:parseType="Resource">
            <rs:variable>value</rs:variable><rs:value>Bob</rs:value>
          </rs:binding>
        </rs:solution>
      </rs:ResultSet>
    </rdf:RDF>"""
    correct = select_xml([
        literal_binding("Alice"),
        literal_binding("Bob"),
    ])
    reversed_rows = select_xml([
        literal_binding("Bob"),
        literal_binding("Alice"),
    ])

    assert compare_rdf_result_set(expected, correct, "rdf")[0] == Status.PASSED
    assert (
        compare_rdf_result_set(expected, reversed_rows, "rdf")[0]
        == Status.FAILED
    )


def test_turtle_result_set_is_detected_semantically():
    assert expected_is_result_set(
        f"@prefix rs: <{RS}> . [] a rs:ResultSet .",
        "ttl",
    )
    assert not expected_is_result_set(
        "@prefix ex: <http://example.org/> . ex:s ex:p ex:o .",
        "ttl",
    )


def test_ordered_results_require_the_actual_xml_order():
    expected = ordered_result(['"Alice"', '"Bob"'])
    correct = select_xml([
        literal_binding("Alice"),
        literal_binding("Bob"),
    ])
    reversed_rows = select_xml([
        literal_binding("Bob"),
        literal_binding("Alice"),
    ])

    assert compare_rdf_result_set(expected, correct, "ttl")[0] == Status.PASSED
    assert (
        compare_rdf_result_set(expected, reversed_rows, "ttl")[0]
        == Status.FAILED
    )


def test_unordered_results_ignore_actual_xml_order():
    expected = ordered_result(['"Alice"', '"Bob"']).replace(
        "rs:index 1 ;", ""
    ).replace("rs:index 2 ;", "")
    reversed_rows = select_xml([
        literal_binding("Bob"),
        literal_binding("Alice"),
    ])
    assert (
        compare_rdf_result_set(expected, reversed_rows, "ttl")[0]
        == Status.PASSED
    )


def test_ordered_duplicate_solutions_are_preserved():
    expected = ordered_result(['"same"', '"same"'])
    duplicate_rows = select_xml([
        literal_binding("same"),
        literal_binding("same"),
    ])
    one_row = select_xml([literal_binding("same")])
    assert (
        compare_rdf_result_set(expected, duplicate_rows, "ttl")[0]
        == Status.PASSED
    )
    assert (
        compare_rdf_result_set(expected, one_row, "ttl")[0]
        == Status.FAILED
    )


def test_large_unordered_duplicate_result_is_compared_as_a_multiset():
    repeated = [
        ("one", "one"),
        ("two", "two"),
        ("three", "three"),
        ("four", "four"),
    ]
    rows = [row for row in repeated for _ in range(9)]
    rows.extend([
        ("unique-1", "unique-a"),
        ("unique-2", "unique-b"),
        ("unique-3", "unique-c"),
        ("unique-4", "unique-d"),
    ])
    solutions = "\n".join(
        f"""rs:solution [ rs:binding
          [ rs:variable "left" ; rs:value "{left}" ],
          [ rs:variable "right" ; rs:value "{right}" ]
        ] ;"""
        for left, right in rows
    )
    expected = f"""@prefix rs: <{RS}> .
    [] a rs:ResultSet ;
       rs:resultVariable "left", "right" ;
       {solutions}
       .
    """
    actual = select_xml(
        [
            literal_binding(left, "left")
            + literal_binding(right, "right")
            for left, right in reversed(rows)
        ],
        variables=("right", "left"),
    )

    assert compare_rdf_result_set(expected, actual, "ttl")[0] == Status.PASSED

    wrong_rows = list(reversed(rows))
    wrong_rows[0] = ("wrong", wrong_rows[0][1])
    wrong = select_xml(
        [
            literal_binding(left, "left")
            + literal_binding(right, "right")
            for left, right in wrong_rows
        ],
        variables=("left", "right"),
    )
    assert compare_rdf_result_set(expected, wrong, "ttl")[0] == Status.FAILED


def test_unordered_result_requires_consistent_bnode_mapping_across_rows():
    expected = f"""@prefix rs: <{RS}> .
    [] a rs:ResultSet ;
       rs:resultVariable "label", "node" ;
       rs:solution [ rs:binding
         [ rs:variable "label" ; rs:value "first" ],
         [ rs:variable "node" ; rs:value _:shared ]
       ] ;
       rs:solution [ rs:binding
         [ rs:variable "label" ; rs:value "second" ],
         [ rs:variable "node" ; rs:value _:shared ]
       ] .
    """
    correct = select_xml(
        [
            literal_binding("second", "label") + bnode_binding("renamed", "node"),
            literal_binding("first", "label") + bnode_binding("renamed", "node"),
        ],
        variables=("node", "label"),
    )
    inconsistent = select_xml(
        [
            literal_binding("first", "label") + bnode_binding("one", "node"),
            literal_binding("second", "label") + bnode_binding("two", "node"),
        ],
        variables=("label", "node"),
    )
    head, _, tail = expected.rpartition("_:shared")
    distinct_expected = head + "_:other" + tail

    assert compare_rdf_result_set(expected, correct, "ttl")[0] == Status.PASSED
    assert (
        compare_rdf_result_set(expected, inconsistent, "ttl")[0]
        == Status.FAILED
    )
    assert (
        compare_rdf_result_set(distinct_expected, correct, "ttl")[0]
        == Status.FAILED
    )


def test_ask_boolean_mismatch_fails_even_with_the_same_graph_size():
    expected = f"""@prefix rs: <{RS}> .
    @prefix xsd: <{rdflib.XSD}> .
    [] a rs:ResultSet ; rs:boolean "true"^^xsd:boolean .
    """
    actual = f"""<sparql xmlns="http://www.w3.org/2005/sparql-results#">
      <head/><boolean>false</boolean>
    </sparql>"""

    assert compare_rdf_result_set(expected, actual, "ttl")[0] == Status.FAILED


def test_configured_datatype_alias_is_an_intended_deviation():
    expected = f"""@prefix rs: <{RS}> .
    @prefix xsd: <{rdflib.XSD}> .
    [] a rs:ResultSet ;
       rs:resultVariable "value" ;
       rs:solution [ rs:binding [
         rs:variable "value" ; rs:value "29"^^xsd:integer
       ] ] .
    """
    actual = select_xml([
        literal_binding(
            "29",
            attributes=f'datatype="{rdflib.XSD.int}"',
        ),
    ])
    aliases = [(str(rdflib.XSD.integer), str(rdflib.XSD.int))]

    assert compare_rdf_result_set(expected, actual, "ttl")[0] == Status.FAILED
    status, error, *_ = compare_rdf_result_set(
        expected,
        actual,
        "ttl",
        alias=aliases,
        number_types=(str(rdflib.XSD.integer), str(rdflib.XSD.int)),
    )
    assert status == Status.INTENDED
    assert error == ErrorMessage.INTENDED_MSG


def test_plain_and_xsd_string_alias_is_an_intended_deviation():
    expected = f"""@prefix rs: <{RS}> .
    @prefix xsd: <{rdflib.XSD}> .
    [] a rs:ResultSet ;
       rs:resultVariable "value" ;
       rs:solution [ rs:binding [
         rs:variable "value" ; rs:value "text"^^xsd:string
       ] ] .
    """
    actual = select_xml([literal_binding("text")])

    status, error, *_ = compare_rdf_result_set(
        expected,
        actual,
        "ttl",
        alias=[(str(rdflib.XSD.string), None)],
    )
    assert status == Status.INTENDED
    assert error == ErrorMessage.INTENDED_MSG


def test_alias_comparison_keeps_order_and_global_bnode_mapping():
    expected = f"""@prefix rs: <{RS}> .
    @prefix xsd: <{rdflib.XSD}> .
    [] a rs:ResultSet ;
       rs:resultVariable "node", "value" ;
       rs:solution [ rs:index 1 ; rs:binding
         [ rs:variable "node" ; rs:value _:shared ],
         [ rs:variable "value" ; rs:value "1.0"^^xsd:float ]
       ] ;
       rs:solution [ rs:index 2 ; rs:binding
         [ rs:variable "node" ; rs:value _:shared ],
         [ rs:variable "value" ; rs:value "2.0"^^xsd:float ]
       ] .
    """
    correct = select_xml(
        [
            bnode_binding("renamed", "node")
            + literal_binding(
                "1",
                attributes=f'datatype="{rdflib.XSD.double}"',
            ),
            bnode_binding("renamed", "node")
            + literal_binding(
                "2",
                attributes=f'datatype="{rdflib.XSD.double}"',
            ),
        ],
        variables=("value", "node"),
    )
    reversed_rows = select_xml(
        [
            bnode_binding("renamed", "node")
            + literal_binding(
                "2",
                attributes=f'datatype="{rdflib.XSD.double}"',
            ),
            bnode_binding("renamed", "node")
            + literal_binding(
                "1",
                attributes=f'datatype="{rdflib.XSD.double}"',
            ),
        ],
        variables=("node", "value"),
    )
    aliases = [(str(rdflib.XSD.float), str(rdflib.XSD.double))]
    number_types = (str(rdflib.XSD.float), str(rdflib.XSD.double))

    assert compare_rdf_result_set(
        expected,
        correct,
        "ttl",
        alias=aliases,
        number_types=number_types,
    )[0] == Status.INTENDED
    assert compare_rdf_result_set(
        expected,
        reversed_rows,
        "ttl",
        alias=aliases,
        number_types=number_types,
    )[0] == Status.FAILED


def test_aliases_do_not_hide_ask_boolean_mismatches():
    expected = f"""@prefix rs: <{RS}> .
    @prefix xsd: <{rdflib.XSD}> .
    [] a rs:ResultSet ; rs:boolean "true"^^xsd:boolean .
    """
    actual = f"""<sparql xmlns="http://www.w3.org/2005/sparql-results#">
      <head/><boolean>false</boolean>
    </sparql>"""

    assert compare_rdf_result_set(
        expected,
        actual,
        "ttl",
        alias=[(str(rdflib.XSD.integer), str(rdflib.XSD.int))],
        number_types=(str(rdflib.XSD.integer), str(rdflib.XSD.int)),
    )[0] == Status.FAILED


@pytest.mark.parametrize(
    "indices",
    [
        ("rs:index 1 ;", ""),
        ('rs:index "first" ;', 'rs:index "second" ;'),
        ("rs:index 1, 2 ;", "rs:index 2 ;"),
        ("rs:index 1 ;", "rs:index 1 ;"),
        ("rs:index 1 ;", "rs:index 3 ;"),
    ],
)
def test_malformed_or_partial_order_indices_are_rejected(indices):
    expected = ordered_result(['"Alice"', '"Bob"'])
    expected = expected.replace("rs:index 1 ;", indices[0])
    expected = expected.replace("rs:index 2 ;", indices[1])
    actual = select_xml([
        literal_binding("Alice"),
        literal_binding("Bob"),
    ])
    with pytest.raises(ValueError, match="rs:index|integer|indices"):
        compare_rdf_result_set(expected, actual, "ttl")


def test_malformed_xml_is_rejected():
    with pytest.raises(ET.ParseError):
        sparql_xml_to_result_set_ttl("<sparql>")


@pytest.mark.parametrize(
    ("query", "expected"),
    [
        ("SELECT * WHERE { ?s ?p ?o }", True),
        ("PREFIX ex: <http://example.org/> ASK { ?s ?p ?o }", True),
        ("# SELECT is only a comment\nCONSTRUCT { ?s ?p ?o } WHERE {}", False),
        ("DESCRIBE <http://example.org/>", False),
    ],
)
def test_query_form_detection(query, expected):
    assert is_select_or_ask(query) is expected
