"""
QLever engine manager with fast in-place graph reset.

Extends QleverBinariesManager with a reset_graphs() override that issues
CLEAR ALL and re-uploads graphs via the SPARQL 1.1 Graph Store HTTP Protocol
instead of restarting the server between tests.  This avoids repeated index
rebuilds for update and protocol test groups.

Falls back to a full teardown + setup if CLEAR ALL or any upload fails.

Usage:  python3 main.py --engine ./qlever-binaries-manager-reset.py ...
"""

import importlib.util
import os
import sys
from pathlib import Path
from typing import Tuple

import requests

from sparql_conformance.config import Config
from sparql_conformance.rdf_tools import rdf_xml_to_turtle
from sparql_conformance.util import read_file

# ---------------------------------------------------------------------------
# Dynamically import QleverBinariesManager from the sibling file so this
# module works without renaming or restructuring the base file.
# ---------------------------------------------------------------------------
_base_path = Path(__file__).parent / "qlever-binaries-manager.py"
_spec = importlib.util.spec_from_file_location("qlever_binaries_manager", _base_path)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
QleverBinariesManager = _mod.QleverBinariesManager


class QleverBinariesManagerWithReset(QleverBinariesManager):
    """QLever engine manager with efficient in-place graph reset."""

    def reset_graphs(
        self,
        config: Config,
        graph_paths: Tuple[Tuple[str, str], ...],
    ) -> bool:
        """Reset graphs via CLEAR ALL + Graph Store HTTP PUT.

        Avoids tearing down and rebuilding the index between tests in the same
        graph group.  Falls back to a full restart on any failure.
        """
        status, _ = self.update(config, "CLEAR ALL")
        if not (200 <= status < 300):
            return self._full_restart(config, graph_paths)

        base_url = f"http://{config.server_address}:{config.port}/sparql"
        for graph_path, graph_name in graph_paths:
            ttl_content = self._to_turtle(graph_path, graph_name)
            if ttl_content is None:
                return self._full_restart(config, graph_paths)

            if graph_name == "-":
                params = {"default": "", "access-token": "abc"}
            else:
                params = {"graph": graph_name, "access-token": "abc"}

            try:
                r = requests.put(
                    base_url,
                    params=params,
                    data=ttl_content.encode("utf-8"),
                    headers={"Content-Type": "text/turtle"},
                    timeout=60,
                )
                if not (200 <= r.status_code < 300):
                    return self._full_restart(config, graph_paths)
            except requests.exceptions.RequestException:
                return self._full_restart(config, graph_paths)

        return True

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _to_turtle(self, graph_path: str, graph_name: str):
        """Return the graph file content as a Turtle string, or None on error."""
        try:
            if graph_path.endswith(".rdf"):
                return rdf_xml_to_turtle(graph_path, graph_name)
            return read_file(graph_path)
        except Exception:
            return None

    def _full_restart(
        self,
        config: Config,
        graph_paths: Tuple[Tuple[str, str], ...],
    ) -> bool:
        self.cleanup(config)
        ok_i, ok_s, _, _ = self.setup(config, graph_paths)
        return ok_i and ok_s
