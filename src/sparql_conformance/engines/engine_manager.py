from abc import ABC, abstractmethod
import re
from typing import Set, Tuple

from sparql_conformance.config import Config
from sparql_conformance.util import read_file


# Graph Store Protocol features a test may declare via mf:requires
# (local names of the mf: URIs used in the graph-store-protocol manifests).
ALL_GRAPHSTORE_FEATURES = {
    "DirectGraphIdentification",
    "IndirectGraphIdentification",
    "POSTGraphCreation",
}


def has_uri_scheme(value: str) -> bool:
    """Return whether ``value`` starts with an RFC 3986 URI scheme."""
    return bool(re.match(r"^[A-Za-z][A-Za-z0-9+.-]*:", value or ""))


class EngineManager(ABC):
    """Abstract base class for SPARQL engine managers"""

    @abstractmethod
    def setup(self,
              config: Config,
              graph_paths: Tuple[Tuple[str, str], ...]
              ) -> Tuple[bool, bool, str, str]:
        """
        Set up the engine for testing.

        Args:
            config: Test suite config, used to set engine-specific settings
            graph_paths: ex. default graph + named graph (('graph_path', '-'),
                            ('graph_path2', 'graph_name2'))

        Returns:
            index_success (bool), server_success (bool), index_log (str), server_log (str)
        """
        pass

    @abstractmethod
    def cleanup(self, config: Config):
        """Clean up the test environment after testing"""
        pass

    @abstractmethod
    def query(self, config: Config, query: str, result_format: str) -> Tuple[int, str]:
        """
        Send a SPARQL query to the engine and return the result

        Args:
            config: Test suite config, used to set engine-specific settings
            query: The SPARQL query to be executed
            result_format: Requested wire format. Managers should return that
                format without converting it to a test-suite-specific expected
                representation.

        Returns:
           HTTP status code (int), query result (str)
        """
        pass

    @abstractmethod
    def update(self, config: Config, query: str) -> Tuple[int, str]:
        """
        Send a SPARQL update query to the engine and return the result

        Args:
            config: Test suite config, used to set engine-specific settings
            query: The SPARQL update query to be executed

        Returns:
           HTTP status code (int), response (str)
        """
        pass

    @abstractmethod
    def protocol_endpoint(self) -> str:
        """
        Returns the name of the protocol endpoint for the engine.
        Used to replace the standard endpoint with the
        engine-specific endpoint in the protocol tests.
        Ex. POST /sparql/ HTTP/1.1 -> POST /qlever/ HTTP/1.1
        """
        pass

    def protocol_update_endpoint(self) -> str:
        """
        Returns the endpoint for protocol update requests.

        Engines with a dedicated update route can override this.
        Default is to reuse the query protocol endpoint.
        """
        return self.protocol_endpoint()

    def graph_store_endpoint(self) -> str:
        """Return the endpoint used by Graph Store Protocol tests.

        ``--graph-store`` can override this value. Most engines expose their
        graph store at ``sparql``, so that remains the default for custom
        managers that do not override this method.
        """
        return "sparql"

    def default_graph_construct_query(self) -> str:
        """
        Returns a CONSTRUCT query that retrieves all triples from the default graph.

        Engines that store the default graph under a named graph IRI (e.g. QLever's
        ql:default-graph) must override this to use the appropriate GRAPH clause.
        """
        return "CONSTRUCT {?s ?p ?o} WHERE { ?s ?p ?o }"

    def reset_graphs(
        self,
        config: Config,
        graph_paths: Tuple[Tuple[str, str], ...],
    ) -> bool:
        """Restore the engine to the given initial graph state without restarting.

        Called between consecutive tests in the same graph group so that each
        test starts from a known clean state.  The default performs a full
        teardown + setup (always correct).  Engines that support a cheaper
        in-place reset (e.g. CLEAR ALL + HTTP re-upload) should override this
        to avoid repeated server startups.

        Returns True on success, False if the engine could not be reset.
        """
        self.cleanup(config)
        ok_i, ok_s, _, _ = self.setup(config, graph_paths)
        return ok_i and ok_s

    def supported_graphstore_features(self) -> Set[str]:
        """
        Return the Graph Store Protocol features this engine supports.

        Values are the local names of the mf: feature URIs that GSP tests
        declare via mf:requires (e.g. "DirectGraphIdentification",
        "IndirectGraphIdentification", "POSTGraphCreation"). A structured GSP
        test whose mf:requires are not all supported is skipped (reported as an
        intended deviation) rather than run and failed.

        Default assumes full support so engines that do not override keep their
        previous behaviour of running every test. Engines lacking a feature
        should override and return only the features they actually support.
        """
        return set(ALL_GRAPHSTORE_FEATURES)

    def activate_syntax_test_mode(self, config: Config):
        """
        Called once before syntax tests run, after the server has started.

        Override this if the engine needs a one-time configuration call to return
        proper error responses for syntactically invalid queries (rather than
        silently accepting them). Default is a no-op.
        """
        pass

    def get_server_log(self, config: Config) -> str:
        """
        Return the engine's server log for the current run ("" if there is
        none). Called after each test group so the log can be attached to the
        tests' results.

        The default reads ./<run_id>.server-log.txt, which is where the
        built-in managers write it. Engines that log elsewhere should
        override this.
        """
        return read_file(f"./{config.run_id}.server-log.txt")
