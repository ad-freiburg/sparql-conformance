"""Helpers for RDF-encoded SPARQL result sets used by legacy test suites."""

from collections import Counter
from dataclasses import dataclass
import math
import xml.etree.ElementTree as ET
from typing import Callable, Dict, FrozenSet, Hashable, Iterable, Optional, Tuple

import rdflib
from rdflib.plugins.sparql.parser import parseQuery


SPARQL_RESULTS_NS = "http://www.w3.org/2005/sparql-results#"
RESULT_SET = rdflib.Namespace(
    "http://www.w3.org/2001/sw/DataAccess/tests/result-set#"
)
RESULT_SET_INDEX = RESULT_SET["index"]


RdfTerm = rdflib.term.Identifier
Binding = Tuple[str, RdfTerm]
Solution = Tuple[Binding, ...]
TermKey = Callable[[RdfTerm], Hashable]


@dataclass(frozen=True)
class _ResultSetValue:
    """Logical contents of an RDF result set, without structural blank nodes."""

    variables: FrozenSet[str]
    boolean: Optional[RdfTerm]
    solutions: Tuple[Solution, ...]
    ordered: bool = False


def is_select_or_ask(query: str) -> bool:
    """Return whether RDFLib parses ``query`` as SELECT or ASK."""
    try:
        query_form = parseQuery(query)[1].name
    except Exception:
        return False
    return query_form in ("SelectQuery", "AskQuery")


def _new_result_set_graph():
    graph = rdflib.Graph()
    graph.bind("rs", RESULT_SET)
    result_set = rdflib.BNode()
    graph.add((result_set, rdflib.RDF.type, RESULT_SET.ResultSet))
    return graph, result_set


def _add_boolean(graph, result_set, value) -> str:
    graph.add(
        (
            result_set,
            RESULT_SET.boolean,
            rdflib.Literal(value, datatype=rdflib.XSD.boolean),
        )
    )
    return graph.serialize(format="turtle")


def _add_binding(graph, solution, name, value) -> None:
    binding = rdflib.BNode()
    graph.add((solution, RESULT_SET.binding, binding))
    graph.add((binding, RESULT_SET.variable, rdflib.Literal(name)))
    graph.add((binding, RESULT_SET.value, value))


def sparql_xml_to_result_set_ttl(xml_string: str) -> str:
    """Convert SPARQL Results XML to the SPARQL 1.0 result-set vocabulary."""
    root = ET.fromstring(xml_string)
    graph, result_set = _new_result_set_graph()
    ns = SPARQL_RESULTS_NS

    boolean = root.find(f"{{{ns}}}boolean")
    if boolean is not None:
        value = (boolean.text or "").strip().lower() == "true"
        return _add_boolean(graph, result_set, value)

    head = root.find(f"{{{ns}}}head")
    if head is not None:
        for variable in head.findall(f"{{{ns}}}variable"):
            graph.add(
                (
                    result_set,
                    RESULT_SET.resultVariable,
                    rdflib.Literal(variable.get("name")),
                )
            )

    results = root.find(f"{{{ns}}}results")
    if results is not None:
        for index, result in enumerate(
            results.findall(f"{{{ns}}}result"), start=1
        ):
            solution = rdflib.BNode()
            graph.add((result_set, RESULT_SET.solution, solution))
            graph.add(
                (
                    solution,
                    RESULT_SET_INDEX,
                    rdflib.Literal(index, datatype=rdflib.XSD.integer),
                )
            )
            for binding in result.findall(f"{{{ns}}}binding"):
                name = binding.get("name")
                uri = binding.find(f"{{{ns}}}uri")
                literal = binding.find(f"{{{ns}}}literal")
                bnode = binding.find(f"{{{ns}}}bnode")

                if uri is not None:
                    value = rdflib.URIRef((uri.text or "").strip())
                elif literal is not None:
                    text = literal.text or ""
                    datatype = literal.get("datatype")
                    language = literal.get(
                        "{http://www.w3.org/XML/1998/namespace}lang"
                    )
                    if datatype:
                        value = rdflib.Literal(
                            text, datatype=rdflib.URIRef(datatype)
                        )
                    elif language:
                        value = rdflib.Literal(text, lang=language)
                    else:
                        value = rdflib.Literal(text)
                elif bnode is not None:
                    value = rdflib.BNode((bnode.text or "").strip())
                else:
                    continue
                _add_binding(graph, solution, name, value)

    return graph.serialize(format="turtle")


def parse_expected_rdf(
    rdf_string: str,
    rdf_format: str,
    public_id: str | None = None,
) -> rdflib.Graph:
    """Parse an RDF expectation using the format implied by its extension."""
    formats = {"rdf": "xml", "ttl": "turtle"}
    if rdf_format not in formats:
        raise ValueError(f"Unsupported RDF expectation format: {rdf_format}")
    graph = rdflib.Graph()
    graph.parse(
        data=rdf_string,
        format=formats[rdf_format],
        publicID=public_id,
    )
    return graph


def is_result_set_graph(graph: rdflib.Graph) -> bool:
    """Return whether an RDF graph semantically contains an rs:ResultSet."""
    return any(graph.subjects(rdflib.RDF.type, RESULT_SET.ResultSet))


def expected_is_result_set(
    rdf_string: str,
    rdf_format: str,
    public_id: str | None = None,
) -> bool:
    """Return whether a Turtle or RDF/XML expectation is an RDF result set."""
    if rdf_format not in ("rdf", "ttl"):
        return False
    return is_result_set_graph(
        parse_expected_rdf(rdf_string, rdf_format, public_id)
    )


def _expected_solution_index(
    graph: rdflib.Graph,
    solution: RdfTerm,
) -> Optional[int]:
    """Return and validate one solution's optional ``rs:index`` value."""
    values = list(graph.objects(solution, RESULT_SET_INDEX))
    if not values:
        return None
    if len(values) != 1:
        raise ValueError(
            "Ordered RDF result sets require exactly one rs:index per "
            "solution."
        )
    value = values[0]
    python_value = (
        value.toPython() if isinstance(value, rdflib.Literal) else None
    )
    if (
        not isinstance(value, rdflib.Literal)
        or isinstance(python_value, bool)
        or not isinstance(python_value, int)
    ):
        raise ValueError(
            "Every rs:index in an ordered RDF result set must be an "
            "integer literal."
        )
    return python_value


def _rdf_solution(graph: rdflib.Graph, solution: RdfTerm) -> Solution:
    """Extract one solution and validate its binding structure."""
    bindings: Dict[str, RdfTerm] = {}
    for binding in graph.objects(solution, RESULT_SET.binding):
        variables = list(graph.objects(binding, RESULT_SET.variable))
        values = list(graph.objects(binding, RESULT_SET.value))
        if len(variables) != 1 or len(values) != 1:
            raise ValueError(
                "Every result binding requires exactly one rs:variable and "
                "one rs:value."
            )
        variable = variables[0]
        if not isinstance(variable, rdflib.Literal):
            raise ValueError("Every rs:variable must be a literal.")
        name = str(variable)
        if name in bindings:
            raise ValueError(
                f"A result solution binds variable {name!r} more than once."
            )
        bindings[name] = values[0]
    return tuple(sorted(bindings.items(), key=lambda item: item[0]))


def _parse_result_set_graph(
    graph: rdflib.Graph,
    ordered: Optional[bool] = None,
) -> _ResultSetValue:
    """Extract a logical result set while discarding structural blank nodes."""
    roots = list(graph.subjects(rdflib.RDF.type, RESULT_SET.ResultSet))
    if len(roots) != 1:
        raise ValueError("Expected RDF must contain exactly one rs:ResultSet.")
    result_set = roots[0]

    variable_terms = list(graph.objects(result_set, RESULT_SET.resultVariable))
    if any(not isinstance(value, rdflib.Literal) for value in variable_terms):
        raise ValueError("Every rs:resultVariable must be a literal.")
    variables = frozenset(str(value) for value in variable_terms)

    booleans = list(graph.objects(result_set, RESULT_SET.boolean))
    solution_nodes = list(graph.objects(result_set, RESULT_SET.solution))
    if booleans:
        if len(booleans) != 1 or solution_nodes or variables:
            raise ValueError(
                "An ASK result requires one rs:boolean and no SELECT content."
            )
        boolean = booleans[0]
        if not isinstance(boolean, rdflib.Literal):
            raise ValueError("The rs:boolean value must be a literal.")
        python_value = boolean.toPython()
        if not isinstance(python_value, bool):
            raise ValueError("The rs:boolean value must be a boolean literal.")
        return _ResultSetValue(
            variables=frozenset(),
            boolean=rdflib.Literal(
                python_value,
                datatype=rdflib.XSD.boolean,
            ),
            solutions=(),
        )

    indexed_solutions = [
        (
            _expected_solution_index(graph, solution),
            _rdf_solution(graph, solution),
        )
        for solution in solution_nodes
    ]
    has_indices = any(index is not None for index, _ in indexed_solutions)
    if ordered is None:
        ordered = has_indices
    if ordered and any(index is None for index, _ in indexed_solutions):
        raise ValueError(
            "Ordered RDF result sets require exactly one rs:index per solution."
        )
    if ordered:
        indices = [
            index for index, _ in indexed_solutions if index is not None
        ]
        if sorted(indices) != list(range(1, len(indices) + 1)):
            raise ValueError(
                "Ordered RDF result-set indices must be unique and contiguous "
                "starting at 1."
            )
        indexed_solutions.sort(key=lambda item: item[0])

    return _ResultSetValue(
        variables=variables,
        boolean=None,
        solutions=tuple(solution for _, solution in indexed_solutions),
        ordered=ordered,
    )


def _contains_bnode(solution: Solution) -> bool:
    return any(isinstance(value, rdflib.BNode) for _, value in solution)


def _exact_term_key(value: RdfTerm) -> Hashable:
    """Return the RDF term itself for strict result-set comparison."""
    return value


def _alias_term_key(
    alias: Iterable[Tuple[Optional[str], Optional[str]]],
    number_types: Iterable[str],
) -> TermKey:
    """Build a key function that applies configured datatype aliases."""
    parents: Dict[Optional[str], Optional[str]] = {}

    def find(value: Optional[str]) -> Optional[str]:
        parents.setdefault(value, value)
        parent = parents[value]
        if parent != value:
            parents[value] = find(parent)
        return parents[value]

    def union(left: Optional[str], right: Optional[str]) -> None:
        left_root = find(left)
        right_root = find(right)
        if left_root != right_root:
            parents[right_root] = left_root

    for left, right in alias:
        union(left, right)

    numeric_datatypes = frozenset(number_types)

    def term_key(value: RdfTerm) -> Hashable:
        if not isinstance(value, rdflib.Literal):
            return value
        datatype = str(value.datatype) if value.datatype is not None else None
        canonical_datatype = find(datatype)
        lexical_value: Hashable = str(value)
        if datatype in numeric_datatypes:
            try:
                numeric_value = float(str(value))
                if math.isnan(numeric_value):
                    lexical_value = ("nan",)
                elif math.isinf(numeric_value):
                    lexical_value = ("infinity", numeric_value > 0)
                else:
                    lexical_value = numeric_value
            except ValueError:
                pass
        return (
            "literal",
            canonical_datatype,
            value.language.lower() if value.language else None,
            lexical_value,
        )

    return term_key


def _solution_signature(
    solution: Solution,
    term_key: TermKey,
) -> Tuple[tuple, ...]:
    """Return a blank-node-independent candidate-matching signature."""
    return tuple(
        (
            name,
            None if isinstance(value, rdflib.BNode) else term_key(value),
        )
        for name, value in solution
    )


def _match_solution(
    expected: Solution,
    actual: Solution,
    expected_to_actual: Dict[RdfTerm, RdfTerm],
    actual_to_expected: Dict[RdfTerm, RdfTerm],
    term_key: TermKey,
) -> Optional[Tuple[Dict[RdfTerm, RdfTerm], Dict[RdfTerm, RdfTerm]]]:
    """Match two rows while extending a consistent blank-node bijection."""
    if _solution_signature(expected, term_key) != _solution_signature(
        actual,
        term_key,
    ):
        return None
    forward = expected_to_actual.copy()
    reverse = actual_to_expected.copy()
    for (_, expected_value), (_, actual_value) in zip(expected, actual):
        if not isinstance(expected_value, rdflib.BNode):
            continue
        if not isinstance(actual_value, rdflib.BNode):
            return None
        mapped = forward.get(expected_value)
        reverse_mapped = reverse.get(actual_value)
        if mapped is not None and mapped != actual_value:
            return None
        if reverse_mapped is not None and reverse_mapped != expected_value:
            return None
        forward[expected_value] = actual_value
        reverse[actual_value] = expected_value
    return forward, reverse


def _match_bnode_solutions(
    expected: Tuple[Solution, ...],
    actual: Tuple[Solution, ...],
    term_key: TermKey,
) -> bool:
    """Match unordered blank-node-bearing rows with a global bijection."""
    if len(expected) != len(actual):
        return False
    candidates = {
        index: [
            actual_index
            for actual_index, actual_solution in enumerate(actual)
            if _solution_signature(solution, term_key)
            == _solution_signature(actual_solution, term_key)
        ]
        for index, solution in enumerate(expected)
    }
    order = sorted(candidates, key=lambda index: len(candidates[index]))
    if any(not candidates[index] for index in order):
        return False

    def search(
        position: int,
        used: FrozenSet[int],
        forward: Dict[RdfTerm, RdfTerm],
        reverse: Dict[RdfTerm, RdfTerm],
    ) -> bool:
        if position == len(order):
            return True
        expected_index = order[position]
        for actual_index in candidates[expected_index]:
            if actual_index in used:
                continue
            mappings = _match_solution(
                expected[expected_index],
                actual[actual_index],
                forward,
                reverse,
                term_key,
            )
            if mappings is not None and search(
                position + 1,
                used | frozenset((actual_index,)),
                mappings[0],
                mappings[1],
            ):
                return True
        return False

    return search(0, frozenset(), {}, {})


def _result_sets_equal(
    expected: _ResultSetValue,
    actual: _ResultSetValue,
    term_key: TermKey = _exact_term_key,
) -> bool:
    """Compare two logical result sets without structural graph isomorphism."""
    if expected.variables != actual.variables:
        return False
    if expected.boolean is not None or actual.boolean is not None:
        return expected.boolean == actual.boolean
    if len(expected.solutions) != len(actual.solutions):
        return False

    if expected.ordered:
        forward: Dict[RdfTerm, RdfTerm] = {}
        reverse: Dict[RdfTerm, RdfTerm] = {}
        for expected_solution, actual_solution in zip(
            expected.solutions,
            actual.solutions,
        ):
            mappings = _match_solution(
                expected_solution,
                actual_solution,
                forward,
                reverse,
                term_key,
            )
            if mappings is None:
                return False
            forward, reverse = mappings
        return True

    expected_plain = Counter(
        _solution_signature(solution, term_key)
        for solution in expected.solutions
        if not _contains_bnode(solution)
    )
    actual_plain = Counter(
        _solution_signature(solution, term_key)
        for solution in actual.solutions
        if not _contains_bnode(solution)
    )
    if expected_plain != actual_plain:
        return False
    expected_bnodes = tuple(
        solution for solution in expected.solutions if _contains_bnode(solution)
    )
    actual_bnodes = tuple(
        solution for solution in actual.solutions if _contains_bnode(solution)
    )
    return _match_bnode_solutions(
        expected_bnodes,
        actual_bnodes,
        term_key,
    )


def _describe_result_set(result: _ResultSetValue) -> str:
    """Build a compact, deterministic diagnostic representation."""
    if result.boolean is not None:
        return f"boolean: {result.boolean.n3()}"
    lines = ["variables: " + ", ".join(sorted(result.variables))]
    for solution in result.solutions:
        bindings = ", ".join(
            f"{name}={value.n3()}" for name, value in solution
        )
        lines.append("{" + bindings + "}")
    return "\n".join(lines)


def _actual_result_turtle(graph: rdflib.Graph, ordered: bool) -> str:
    """Render an actual result graph in the legacy format for reports."""
    if not ordered:
        graph.remove((None, RESULT_SET_INDEX, None))
    return graph.serialize(format="turtle")


def compare_rdf_result_set(
    expected_rdf: str,
    actual_xml: str,
    expected_format: str,
    public_id: str | None = None,
    alias: Iterable[Tuple[Optional[str], Optional[str]]] = (),
    number_types: Iterable[str] = (),
) -> tuple:
    """Compare an RDF result-set expectation with SPARQL Results XML."""
    from sparql_conformance.test_object import ErrorMessage, Status
    from sparql_conformance.util import escape

    expected_graph = parse_expected_rdf(
        expected_rdf,
        expected_format,
        public_id,
    )
    if not is_result_set_graph(expected_graph):
        raise ValueError("Expected RDF graph is not an rs:ResultSet.")

    expected = _parse_result_set_graph(expected_graph)
    actual_graph = rdflib.Graph()
    actual_graph.parse(
        data=sparql_xml_to_result_set_ttl(actual_xml),
        format="turtle",
    )
    actual = _parse_result_set_graph(actual_graph, ordered=expected.ordered)
    actual_turtle = _actual_result_turtle(actual_graph, expected.ordered)
    if _result_sets_equal(expected, actual):
        return (
            Status.PASSED,
            "",
            escape(expected_rdf),
            escape(actual_turtle),
            "",
            "",
        )

    if alias and _result_sets_equal(
        expected,
        actual,
        _alias_term_key(alias, number_types),
    ):
        expected_summary = escape(_describe_result_set(expected))
        actual_summary = escape(_describe_result_set(actual))
        return (
            Status.INTENDED,
            ErrorMessage.INTENDED_MSG,
            escape(expected_rdf),
            escape(actual_turtle),
            f'<label class="yellow">{expected_summary}</label>',
            f'<label class="yellow">{actual_summary}</label>',
        )

    expected_summary = escape(_describe_result_set(expected))
    actual_summary = escape(_describe_result_set(actual))
    return (
        Status.FAILED,
        ErrorMessage.RESULTS_NOT_THE_SAME,
        escape(expected_rdf),
        escape(actual_turtle),
        f'<label class="red">{expected_summary}</label>',
        f'<label class="red">{actual_summary}</label>',
    )
