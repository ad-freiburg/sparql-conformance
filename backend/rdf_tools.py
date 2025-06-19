import rdflib
from backend.models import FAILED, PASSED, RESULTS_NOT_THE_SAME, FORMAT_ERROR
import os
import re
from backend.util import escape


def rdf_xml_to_turtle(file_path, public_id) -> str:
    graph = rdflib.Graph()
    graph.parse(file_path, format="xml", publicID=public_id)
    return graph.serialize(format="turtle")


def remove_prefix(turtle_string: str) -> str:
    split = turtle_string.split("\n")
    result = split
    for line in split:
        if line.startswith("@prefix") or line.startswith("PREFIX"):
            result.remove(line)
    return "\n".join(result)


def write_ttl_file(name: str, ttl_string: str):
    f = open(name, "w", encoding="utf-8")
    f.write(ttl_string)
    f.close()


def delete_ttl_file(name: str):
    if os.path.exists(name):
        os.remove(name)


def copy_namespaces(source_graph, target_graph):
    for prefix, namespace in source_graph.namespaces():
        target_graph.bind(prefix, namespace, override=False)


def highlight_differences(turtle_data, diff):
    # Serialize the main graph to turtle (escaped for HTML rendering)
    serialized_turtle = escape(turtle_data.serialize(format="turtle"))
    
    for s, p, o in diff:
        s_prefixed = s.n3(namespace_manager=turtle_data.namespace_manager)
        p_prefixed = p.n3(namespace_manager=turtle_data.namespace_manager)
        o_prefixed = o.n3(namespace_manager=turtle_data.namespace_manager)

        # Escape for matching
        s_escaped = re.escape(escape(s_prefixed))
        p_escaped = re.escape(escape(p_prefixed))
        o_escaped = re.escape(escape(o_prefixed))

        # This matches the whole line of the triple.
        pattern = rf"{s_escaped}(?:[^.]*?)?{p_escaped}\s+(?:[^.]*?){o_escaped}[^.]*?\s+\.(?!</label>)"

        def replace_first_match(match):
            return f'<label class="red">{match.group()}</label>'

        serialized_turtle = re.sub(
            pattern,
            replace_first_match,
            serialized_turtle,
            flags=re.DOTALL
        )

    return serialized_turtle

def compare_ttl(expected_ttl: str, query_ttl: str) -> tuple:
    """
    Compares two XML documents, identifies differences and generates HTML representations.

    This method compares two XML documents and identifies differences.
    It removes equal elements in both documents and generates HTML representations highlighting the remaining differences.

    Parameters:
        expected_xml (str): The expected XML content as a string.
        query_xml (str): The query XML content as a string.

    Returns:
        tuple (bool,str,str,str,str,str): A tuple containing the status, error type and the strings XML1, XML2, XML1 RED, XML2 RED
    """
    status = FAILED
    error_type = RESULTS_NOT_THE_SAME
    expected_graph = rdflib.Graph()
    query_graph = rdflib.Graph()

    expected_graph.parse(data=expected_ttl, format="turtle")
    try:
        query_graph.parse(data=query_ttl, format="turtle")
    except Exception as e:
        error_type = FORMAT_ERROR
        escaped_querty = f'<label class="red">{escape(query_ttl)}</label>'
        escaped_expected = f'<label class="red">{escape(expected_ttl)}</label>'
        return status, error_type, escape(
            expected_ttl), escaped_querty, escaped_expected, f'<label class="red">{e}</label>'

    is_isomorphic = expected_graph.isomorphic(query_graph)

    if is_isomorphic:
        status = PASSED
        error_type = ""
        expected_string = escape(expected_ttl)
        query_string = escape(query_ttl)
        expected_string_red = ""
        query_string_red = ""
    else:
        triples_in_expected_not_in_query = expected_graph - query_graph
        triples_in_query_not_in_expected = query_graph - expected_graph

        # Repair namespaces
        copy_namespaces(expected_graph, triples_in_expected_not_in_query)
        copy_namespaces(query_graph, triples_in_query_not_in_expected)
        expected_string = highlight_differences(
            expected_graph, triples_in_expected_not_in_query)
        query_string = highlight_differences(
            query_graph, triples_in_query_not_in_expected)

        no_prefix_escaped_expected = escape(
            remove_prefix(
                triples_in_expected_not_in_query.serialize(
                    format="turtle")))
        no_prefix_escaped_query = escape(
            remove_prefix(
                triples_in_query_not_in_expected.serialize(
                    format="turtle")))
        expected_string_red = f'<label class="red">{no_prefix_escaped_expected}</label>'
        query_string_red = f'<label class="red">{no_prefix_escaped_query}</label>'

    return status, error_type, expected_string, query_string, expected_string_red, query_string_red
