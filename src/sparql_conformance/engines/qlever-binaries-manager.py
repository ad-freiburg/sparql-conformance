"""
QLever engine manager that calls qlever binaries (qlever-index, qlever-server)
directly via subprocess, with no dependency on qlever-control.

Requires the src package to be installed (e.g. via qlever-control).
Usage:  python3 main.py --engine ./qlever-binaries-manager.py --binaries-directory /path/to/bin ...
"""

import json
import os
import shutil
import subprocess
import time
from pathlib import Path
from typing import Tuple, Optional

import requests

from sparql_conformance.config import Config
from sparql_conformance.engines.engine_manager import EngineManager
from sparql_conformance.rdf_tools import rdf_xml_to_turtle, write_ttl_file, delete_ttl_file
from sparql_conformance.util import get_accept_header, read_file, remove_date_time_parts

_INDEX_NAME = "qlever-sparql-conformance"
_SETTINGS_CONTENT = '{ "num-triples-per-batch": 1000000 }'

_FORMAT_BY_EXTENSION = {
    ".ttl": "ttl",
    ".trig": "trig",
    ".nt": "nt",
    ".nq": "nq",
    ".rdf": "rdf",
    ".xml": "rdf",
}

_SERVER_POLL_RETRIES = 20
_SERVER_POLL_INTERVAL = 0.25


class QleverBinariesManager(EngineManager):
    """QLever engine manager using direct binary invocation."""

    def __init__(self):
        self._server_process: Optional[subprocess.Popen] = None

    # ------------------------------------------------------------------
    # EngineManager interface
    # ------------------------------------------------------------------

    def setup(
        self,
        config: Config,
        graph_paths: Tuple[Tuple[str, str], ...],
    ) -> Tuple[bool, bool, str, str]:
        local_graphs = self._prepare_graph_files(graph_paths)
        index_success, index_log = self._build_index(config, local_graphs)
        for path, _ in local_graphs:
            delete_ttl_file(path)
        if not index_success:
            return False, False, index_log, ""
        server_success, server_log = self._start_server(config)
        return index_success, server_success, index_log, server_log

    def cleanup(self, config: Config):
        self._stop_server()
        subprocess.run(
            f"pkill -f 'qlever-server.*-p {config.port}'",
            shell=True,
            capture_output=True,
        )
        subprocess.run(
            f"rm -f {_INDEX_NAME}*",
            shell=True,
            capture_output=True,
        )

    def query(self, config: Config, query: str, result_format: str) -> Tuple[int, str]:
        return self._http_request(config, query, "application/sparql-query", result_format)

    def update(self, config: Config, query: str) -> Tuple[int, str]:
        return self._http_request(config, query, "application/sparql-update", "json")

    def protocol_endpoint(self) -> str:
        return "sparql"

    def graph_store_endpoint(self) -> str:
        return "http-graph-store"

    def default_graph_construct_query(self) -> str:
        return "CONSTRUCT {?s ?p ?o} WHERE { GRAPH ql:default-graph {?s ?p ?o}}"

    def activate_syntax_test_mode(self, config: Config):
        url = f"http://{config.server_address}:{config.port}"
        params = {
            "access-token": config.access_token,
            "syntax-test-mode": "true",
        }
        try:
            requests.get(url, params=params, timeout=5)
        except requests.exceptions.RequestException:
            pass

    def get_server_log(self, config: Config) -> str:
        # This manager logs under the fixed index name, not the run id.
        return read_file(f"{_INDEX_NAME}.server-log.txt")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _binary(self, config: Config, name: str) -> str:
        if config.path_to_binaries:
            return str(Path(config.path_to_binaries) / name)
        return name

    def _prepare_graph_files(
        self, graph_paths: Tuple[Tuple[str, str], ...]
    ) -> list:
        """Convert .rdf files to .ttl and copy others to the working directory."""
        result = []
        for graph_path, graph_name in graph_paths:
            if graph_path.endswith(".rdf"):
                local_name = Path(graph_path).stem + ".ttl"
                write_ttl_file(local_name, rdf_xml_to_turtle(graph_path, graph_name))
                result.append((local_name, graph_name))
            else:
                src = Path(graph_path).resolve()
                dest = Path(os.getcwd()) / src.name
                if src != dest:
                    shutil.copy(src, dest)
                result.append((src.name, graph_name))
        return result

    def _build_index(
        self, config: Config, graph_paths: list
    ) -> Tuple[bool, str]:
        settings_file = f"{_INDEX_NAME}.settings.json"
        with open(settings_file, "w") as f:
            f.write(_SETTINGS_CONTENT)

        input_parts = []
        for graph_path, graph_name in graph_paths:
            fmt = _FORMAT_BY_EXTENSION.get(Path(graph_path).suffix.lower(), "ttl")
            graph_arg = graph_name if graph_name else "-"
            input_parts.append(f"-f <(cat {graph_path}) -g {graph_arg} -F {fmt} -p false")
        input_options = " ".join(input_parts)

        log_file = f"{_INDEX_NAME}.index-log.txt"
        cmd = (
            f"{self._binary(config, config.index_binary)}"
            f" -i {_INDEX_NAME}"
            f" -s {settings_file}"
            f" --vocabulary-type on-disk-compressed"
            f" {input_options}"
            f" > {log_file} 2>&1"
        )

        try:
            proc = subprocess.run(cmd, shell=True, executable="/bin/bash")
            index_log = read_file(log_file)
            success = proc.returncode == 0 and "Index build completed" in index_log
            return success, remove_date_time_parts(index_log)
        except Exception as e:
            return False, f"Exception running qlever-index: {e}"

    def _start_server(self, config: Config) -> Tuple[bool, str]:
        log_file = f"{_INDEX_NAME}.server-log.txt"
        cmd_args = [
            self._binary(config, config.server_binary),
            '-i', _INDEX_NAME,
            '-j', '1',
            '-p', config.port,
            '-m', '4GB',
            '-c', '2G',
            '-e', '1G',
            '-k', '200',
            '-a', config.access_token,
        ]
        try:
            with open(log_file, 'w') as lf:
                self._server_process = subprocess.Popen(
                    cmd_args, stdout=lf, stderr=subprocess.STDOUT
                )
        except Exception as e:
            return False, f"Exception starting qlever-server: {e}"

        ready = self._wait_for_server(config.server_address, config.port)
        server_log = remove_date_time_parts(read_file(log_file))
        return ready, server_log

    def _wait_for_server(self, address: str, port: str) -> bool:
        url = f"http://{address}:{port}"
        headers = {"Content-type": "application/sparql-query"}
        test_query = "SELECT ?s ?p ?o { ?s ?p ?o } LIMIT 1"
        for _ in range(_SERVER_POLL_RETRIES):
            try:
                r = requests.post(url, headers=headers, data=test_query, timeout=2)
                if r.status_code == 200:
                    return True
            except requests.exceptions.RequestException:
                pass
            time.sleep(_SERVER_POLL_INTERVAL)
        return False

    def _stop_server(self):
        if self._server_process is not None:
            try:
                self._server_process.terminate()
                self._server_process.wait(timeout=10)
            except Exception:
                self._server_process.kill()
            self._server_process = None

    def _http_request(
        self, config: Config, query: str, content_type: str, result_format: str
    ) -> Tuple[int, str]:
        url = f"http://{config.server_address}:{config.port}?access-token={config.access_token}"
        headers = {
            "Accept": get_accept_header(result_format),
            "Content-type": content_type,
        }
        try:
            r = requests.post(url, headers=headers, data=query.encode("utf-8"), timeout=60)
            return r.status_code, r.content.decode("utf-8")
        except requests.exceptions.RequestException as e:
            return 500, f"HTTP Request failed: {e}"
