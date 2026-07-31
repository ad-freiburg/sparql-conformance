import json
import os
from pathlib import Path
from argparse import Namespace
from typing import Tuple, List
import requests

from qlever.commands.query import QueryCommand
from qlever.log import mute_log
from qlever.util import run_command
from qlever.commands.start import StartCommand
from qlever.commands.stop import StopCommand
from sparql_conformance.config import Config
from sparql_conformance.engines.engine_manager import EngineManager
from sparql_conformance import util
from qlever.commands.index import IndexCommand
from sparql_conformance.rdf_tools import write_ttl_file, delete_ttl_file, rdf_xml_to_turtle, replace_empty_base_iri


class QLeverManager(EngineManager):
    """Manager for QLever using docker execution"""

    def update(self, config: Config, query: str) -> Tuple[int, str]:
        return self._query(config, query, "ru", "json")

    def protocol_endpoint(self) -> str:
        return "sparql"

    def graph_store_endpoint(self) -> str:
        return "http-graph-store"

    def cleanup(self, config: Config):
        self._stop_server(config)
        with mute_log():
            run_command(f'rm -f {config.run_id}*')

    def query(self, config: Config, query: str, result_format: str) -> Tuple[int, str]:
        return self._query(config, query, "rq", result_format)

    def _query(self, config: Config, query: str, query_type: str, result_format: str) -> Tuple[int, str]:
        content_type = "query=" if query_type == "rq" else "update="
        args = util.make_args(
            config,
            accept=util.get_accept_header(result_format),
            query=query,
            content_type=content_type,
        )

        try:
            with mute_log():
                qc = QueryCommand()
                qc.execute(args, True)
                body, _, status_line = qc.query_output.rpartition("HTTP_STATUS:")
                status = int(status_line.strip())
            return status, body
        except Exception as e:
            return 1, str(e)

    def setup(self, config: Config, graph_paths: Tuple[Tuple[str, str], ...]) -> Tuple[bool, bool, str, str]:
        server_success = False
        workdir = Path(os.getcwd()).resolve()
        cwd_uri = workdir.as_uri() + "/"
        file_to_named_uri: dict[str, str] = {}
        for gp, gn in graph_paths:
            if gn and gn not in ("-", ""):
                fname = Path(gp).resolve().name
                file_to_named_uri[fname] = gn
        graphs = []
        cleanup_after_index = []
        for graph_path, graph_name in graph_paths:
            src = Path(graph_path).resolve()
            # Handle rdf files by turning them into turtle format.
            if graph_path.endswith(".rdf"):
                graph_path_new = src.name.replace(".rdf", ".ttl")
                write_ttl_file(graph_path_new, rdf_xml_to_turtle(graph_path, graph_name))
                graph_path = graph_path_new
            else:
                replacement = file_to_named_uri.get(src.name, cwd_uri)
                temp_name, temp_path = replace_empty_base_iri(src, workdir, replacement, "qlever")
                if temp_path is not None:
                    graph_path = temp_name
                    cleanup_after_index.append(temp_path)
                else:
                    graph_path = util.copy_graph_to_workdir(graph_path, os.getcwd())
            graphs.append((graph_path, graph_name))

        index_success, index_log = self._index(config, graphs)
        for path, name in graphs:
            delete_ttl_file(path)
        for temp_path in cleanup_after_index:
            try:
                temp_path.unlink()
            except FileNotFoundError:
                pass
        if not index_success:
            return index_success, server_success, index_log, ''
        else:
            server_success, server_log = self._start_server(config)

            if not server_success:
                return index_success, server_success, index_log, server_log
        return index_success, server_success, index_log, server_log

    def _stop_server(self, config: Config) -> Tuple[bool, str]:
        args = Namespace(
            name=config.run_id,
            port=config.port,
            server_container=f'{config.run_id}-server-container',
            no_containers=config.system == 'native',
            show=False,
            cmdline_regex='ServerMain.* -i [^ ]*%%NAME%%'
        )
        try:
            with mute_log(50):
                result = StopCommand().execute(args)
        except Exception as e:
            error_output = str(e)
            return False, error_output
        return result, 'Success'

    def _start_server(self, config: Config) -> Tuple[bool, str]:
        binary = 'qlever-server'
        binary = binary if config.system != 'native' else Path(config.path_to_binaries, binary)
        args = util.make_args(
            config,
            server_binary=binary,
        )
        try:
            with mute_log():
                result = StartCommand().execute(args, called_from_conformance_test=True)
        except Exception as e:
            error_output = str(e)
            return False, error_output

        server_log = ''
        if os.path.exists(f'./{config.run_id}.server-log.txt'):
            server_log = util.read_file(f'./{config.run_id}.server-log.txt')
        return result, server_log

    def _index(self, config: Config, graph_paths: List[Tuple[str, str]]) -> Tuple[bool, str]:
        binary = 'qlever-index'
        index_binary = binary if config.system != 'native' else Path(config.path_to_binaries, binary)
        args = util.make_args(
            config,
            multi_input_json=self._generate_multi_input_json(graph_paths),
            index_binary=index_binary
        )
        try:
            with mute_log():
                result = IndexCommand().execute(args=args, called_from_conformance_test=True)
        except Exception as e:
            error_output = str(e)
            return False, error_output

        index_log = ''
        if os.path.exists(f"./{config.run_id}.index-log.txt"):
            index_log = util.read_file(f"./{config.run_id}.index-log.txt")
        # Docker tee/pipefail workaround: verify the index was actually completed.
        # When QLever index builder fails inside docker, the tee exit code masks
        # the failure and IndexCommand returns True.  meta-data.json is only
        # written on successful completion.
        if result and not os.path.exists(f"{config.run_id}.meta-data.json"):
            result = False
        return result, index_log

    _FORMAT_BY_EXTENSION = {
        '.ttl': 'ttl',
        '.trig': 'trig',
        '.nt': 'nt',
        '.nq': 'nq',
        '.rdf': 'rdf',
        '.xml': 'rdf',
    }

    def _format_for_file(self, path: str) -> str:
        ext = Path(path).suffix.lower()
        return self._FORMAT_BY_EXTENSION.get(ext, 'ttl')

    def _generate_multi_input_json(self, graph_paths: List[Tuple[str, str]]) -> str:
        """Generate the JSON input for multi_input_json in IndexCommand.execute()"""
        input_list = []
        for graph_path, graph_name in graph_paths:
            entry = {
                'cmd': f'cat {graph_path}',
                'graph': graph_name if graph_name else '-',
                'format': self._format_for_file(graph_path)
            }
            input_list.append(entry)
        return json.dumps(input_list)

    def default_graph_construct_query(self) -> str:
        return "CONSTRUCT {?s ?p ?o} WHERE { GRAPH ql:default-graph {?s ?p ?o}}"

    def activate_syntax_test_mode(self, config: Config):
        url = f'http://{config.server_address}:{config.port}'
        params = {
            "access-token": config.access_token,
            "syntax-test-mode": "true"
        }
        requests.get(url, params)
