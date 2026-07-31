"""Resolve and stage dataset sources declared by SPARQL queries."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from urllib.parse import urlsplit
from urllib.request import url2pathname

import rdflib
from rdflib.plugins.sparql.algebra import translateQuery
from rdflib.plugins.sparql.parser import parseQuery


_FROM_KEYWORD = re.compile(r"\bFROM\b", re.IGNORECASE)


@dataclass(frozen=True)
class DatasetSource:
    """A local RDF file staged under the absolute IRI used by the query."""

    local_path: str
    graph_iri: str


@dataclass(frozen=True)
class PreparedQuery:
    """The executable query and the local sources needed by its dataset."""

    query: str
    sources: tuple[DatasetSource, ...]
    setup_error: str = ""


def _resolve_dataset_clauses(
    parsed_query,
    query_uri: str,
) -> list[str]:
    translated = translateQuery(parsed_query, base=query_uri)
    clauses = translated.algebra.get("datasetClause") or []
    resolved: list[str] = []
    for clause in clauses:
        if "default" in clause:
            term = clause["default"]
        elif "named" in clause:
            term = clause["named"]
        else:
            raise ValueError(f"Malformed dataset clause: {clause!r}")
        if not isinstance(term, rdflib.URIRef):
            raise ValueError(f"Unsupported dataset source term: {term!r}")
        resolved.append(str(term))
    return resolved


def _has_explicit_base(parsed_query) -> bool:
    """Return whether the parsed SPARQL prologue declares BASE."""
    return any(
        getattr(declaration, "name", None) == "Base"
        for declaration in parsed_query[0]
    )


def _has_dataset_clauses(parsed_query) -> bool:
    """Return whether the parsed query declares an RDF dataset."""
    query_node = parsed_query[1]
    return (
        "datasetClause" in query_node
        and bool(query_node["datasetClause"])
    )


def _local_path(source_iri: str) -> tuple[str | None, str]:
    parsed = urlsplit(source_iri)
    if parsed.scheme.lower() != "file":
        return None, (
            "Remote dataset source is not available locally and automatic "
            f"fetching is disabled: {source_iri}"
        )
    if parsed.netloc not in ("", "localhost"):
        return None, (
            "Non-local file dataset source is not available and automatic "
            f"fetching is disabled: {source_iri}"
        )
    path = Path(url2pathname(parsed.path)).resolve()
    if not path.is_file():
        return None, f"Dataset source file does not exist: {path}"
    return str(path), ""


def prepare_query_dataset(query: str, query_path: str) -> PreparedQuery:
    """Set the query base and resolve dataset files that need staging."""
    resolved_query_path = Path(query_path).resolve()
    query_uri = resolved_query_path.as_uri()
    try:
        parsed_query = parseQuery(query)
    except Exception as error:
        if not _FROM_KEYWORD.search(query):
            # Query evaluation will report the syntax error. Dataset
            # preparation must not reject engine-specific query syntax.
            return PreparedQuery(query=query, sources=())
        return PreparedQuery(
            query=query,
            sources=(),
            setup_error=f"Could not parse query dataset clauses: {error}",
        )

    execution_query = query
    if not _has_explicit_base(parsed_query):
        query_directory_uri = resolved_query_path.parent.as_uri() + "/"
        execution_query = (
            f"BASE {rdflib.URIRef(query_directory_uri).n3()}\n{query}"
        )

    if not _has_dataset_clauses(parsed_query):
        return PreparedQuery(query=execution_query, sources=())

    try:
        resolved_iris = _resolve_dataset_clauses(parsed_query, query_uri)
    except Exception as error:
        return PreparedQuery(
            query=query,
            sources=(),
            setup_error=f"Could not resolve query dataset clauses: {error}",
        )

    sources: list[DatasetSource] = []
    seen: set[tuple[str, str]] = set()
    for source_iri in resolved_iris:
        local_path, error = _local_path(source_iri)
        if error:
            return PreparedQuery(query=query, sources=(), setup_error=error)
        source = DatasetSource(local_path=local_path, graph_iri=source_iri)
        key = (source.local_path, source.graph_iri)
        if key not in seen:
            seen.add(key)
            sources.append(source)

    return PreparedQuery(query=execution_query, sources=tuple(sources))
