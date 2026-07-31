"""In-process reference engine backed by rdflib.

No server, no docker, no binaries: queries and updates run directly against
an in-memory rdflib Dataset. Used by the framework's own end-to-end tests
(see test/), and as the smallest possible example of an EngineManager.

Supported categories: query, format, update and syntax tests. Protocol and
graph-store-protocol tests need a real HTTP server and are not supported.
"""

from typing import Tuple

import rdflib

from sparql_conformance.config import Config
from sparql_conformance.engines.engine_manager import EngineManager

_RESULT_FORMATS = {
    "srx": "xml",
    "srj": "json",
    "csv": "csv",
    "tsv": "tsv",
}

_GRAPH_FORMATS = {
    ".ttl": "turtle",
    ".trig": "trig",
    ".nt": "nt",
    ".nq": "nquads",
    ".rdf": "xml",
    ".xml": "xml",
}


def _default_graph(dataset: rdflib.Dataset) -> rdflib.Graph:
    # rdflib >= 7.6 names it `default_graph`; older versions `default_context`.
    return getattr(dataset, "default_graph", None) or dataset.default_context


class RdflibEngineManager(EngineManager):
    """EngineManager running SPARQL in-process via rdflib."""

    def __init__(self):
        self._dataset = None

    def setup(
        self,
        config: Config,
        graph_paths: Tuple[Tuple[str, str], ...],
    ) -> Tuple[bool, bool, str, str]:
        self._dataset = rdflib.Dataset()
        try:
            for graph_path, graph_name in graph_paths:
                fmt = _GRAPH_FORMATS.get(
                    "." + graph_path.rsplit(".", 1)[-1].lower(), "turtle"
                )
                if graph_name and graph_name != "-":
                    target = self._dataset.graph(rdflib.URIRef(graph_name))
                else:
                    target = _default_graph(self._dataset)
                target.parse(graph_path, format=fmt)
        except Exception as e:
            return False, False, f"Loading graphs failed: {e}", ""
        return True, True, "", ""

    def cleanup(self, config: Config):
        self._dataset = None

    def query(
        self, config: Config, query: str, result_format: str
    ) -> Tuple[int, str]:
        if self._dataset is None:
            return 500, "No dataset loaded"
        try:
            result = self._dataset.query(query)
        except Exception as e:
            return 400, f"Query failed: {e}"
        try:
            if result.type == "CONSTRUCT" or result.type == "DESCRIBE":
                return 200, result.graph.serialize(format="turtle")
            fmt = _RESULT_FORMATS.get(result_format, "xml")
            serialized = result.serialize(format=fmt)
            if isinstance(serialized, bytes):
                serialized = serialized.decode("utf-8")
            return 200, serialized
        except Exception as e:
            return 500, f"Serializing the result failed: {e}"

    def update(self, config: Config, query: str) -> Tuple[int, str]:
        if self._dataset is None:
            return 500, "No dataset loaded"
        try:
            # Run the update against the default graph (its processor still
            # reaches the dataset's named graphs for GRAPH clauses, since the
            # store is shared); Dataset.update() itself chokes on triple
            # patterns in rdflib 7.x.
            _default_graph(self._dataset).update(query)
        except Exception as e:
            return 400, f"Update failed: {e}"
        return 200, ""

    def protocol_endpoint(self) -> str:
        return "sparql"
