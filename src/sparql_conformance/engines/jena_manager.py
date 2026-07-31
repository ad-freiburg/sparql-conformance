from __future__ import annotations

import os
import re
import urllib.parse
from pathlib import Path

import rdflib

from qjena.commands.index import IndexCommand
from qjena.commands.query import QueryCommand
from qjena.commands.start import StartCommand
from qjena.commands.stop import StopCommand
from qlever.log import mute_log
from qlever.util import run_command
import sparql_conformance.util as conformance_util
from sparql_conformance.config import Config
from sparql_conformance.engines.engine_manager import (
    EngineManager,
    has_uri_scheme,
)
from sparql_conformance.rdf_tools import rdf_xml_to_turtle, write_ttl_file, replace_empty_base_iri


DEFAULT_NAME = "qlever-sparql-conformance"


def _make_args(config: Config, **overrides):
    return getattr(conformance_util, "make_args")(config, **overrides)


def _get_accept_header(result_format: str) -> str:
    return getattr(conformance_util, "get_accept_header")(result_format)


def _read_file(path: str) -> str:
    return getattr(conformance_util, "read_file")(path)


def _copy_graph_to_workdir(file_path: str, workdir: str) -> str:
    return getattr(conformance_util, "copy_graph_to_workdir")(
        file_path, workdir
    )


def _graph_to_trig(turtle_data: str, graph_name: str) -> str:
    graph = rdflib.Graph()
    graph.parse(data=turtle_data, format="turtle")
    dataset = rdflib.ConjunctiveGraph()
    context = dataset.get_context(rdflib.URIRef(graph_name))
    for triple in graph:
        context.add(triple)
    return str(dataset.serialize(format="trig"))


class JenaManager(EngineManager):
    """Manager for Jena using qjena commands."""

    def protocol_endpoint(self) -> str:
        return f"{DEFAULT_NAME}/query"

    def protocol_update_endpoint(self) -> str:
        return f"{DEFAULT_NAME}/update"

    def graph_store_endpoint(self) -> str:
        return f"{DEFAULT_NAME}/data"

    def setup(
        self,
        config: Config,
        graph_paths: tuple[tuple[str, str], ...],
    ) -> tuple[bool, bool, str, str]:
        server_success = False
        graph_files, cleanup_paths = self._prepare_graphs(graph_paths, config)
        index_success, index_log = self._index(config, graph_files)
        self._cleanup_graph_copies(cleanup_paths)
        if not index_success:
            return index_success, server_success, index_log, ""

        server_success, server_log = self._start_server(config)
        if not server_success:
            return index_success, server_success, index_log, server_log
        return index_success, server_success, index_log, server_log

    def cleanup(self, config: Config):
        self._stop_server(config)
        with mute_log():
            run_command(
                f"rm -rf index {config.run_id}.index-log.txt "
                f"{config.run_id}.server-log.txt "
                f"{config.run_id}-fuseki.ttl"
            )

    def reset_graphs(
        self,
        config: Config,
        graph_paths: tuple[tuple[str, str], ...],
    ) -> bool:
        """Clear all graphs and reload initial data via HTTP without restarting Fuseki."""
        status, _ = self.update(config, "CLEAR ALL")
        if status >= 400:
            self.cleanup(config)
            ok_i, ok_s, _, _ = self.setup(config, graph_paths)
            return ok_i and ok_s

        if not graph_paths:
            return True

        workdir = Path(os.getcwd()).resolve()
        cwd_uri = workdir.as_uri() + "/"
        file_to_named_uri: dict[str, str] = {}
        for gp, gn in graph_paths:
            if gn and gn != "-" and not has_uri_scheme(gn):
                fname = Path(gp).resolve().name
                file_to_named_uri[fname] = (
                    f"http://{config.server_address}:{config.port}"
                    f"/{DEFAULT_NAME}/{gn}"
                )

        base_data_url = (
            f"http://{config.server_address}:{config.port}/{DEFAULT_NAME}/data"
        )
        tmp_file = workdir / "_jena_reset_tmp.ttl"
        try:
            for graph_path, graph_name in graph_paths:
                src = Path(graph_path).resolve()
                if src.suffix == ".rdf":
                    turtle_data = rdf_xml_to_turtle(str(src), graph_name)
                else:
                    replacement = file_to_named_uri.get(src.name, cwd_uri)
                    temp_name, temp_path = replace_empty_base_iri(
                        src, workdir, replacement, "jena"
                    )
                    if temp_path is not None:
                        turtle_data = temp_path.read_text(encoding="utf-8")
                        temp_path.unlink()
                    else:
                        turtle_data = src.read_text(encoding="utf-8")

                if graph_name and graph_name != "-":
                    if has_uri_scheme(graph_name):
                        resolved_name = graph_name
                    else:
                        resolved_name = (
                            f"http://{config.server_address}:{config.port}"
                            f"/{DEFAULT_NAME}/{graph_name}"
                        )
                    encoded = urllib.parse.quote(resolved_name, safe="")
                    target_url = f"{base_data_url}?graph={encoded}"
                else:
                    target_url = f"{base_data_url}?default"

                tmp_file.write_text(turtle_data, encoding="utf-8")
                with mute_log():
                    run_command(
                        f'curl -s -X PUT "{target_url}"'
                        f' -H "Content-Type: text/turtle"'
                        f' --data-binary @"{tmp_file}"'
                    )
        finally:
            if tmp_file.exists():
                tmp_file.unlink()
        return True

    def _add_base_if_missing(self, config: Config, query: str) -> str:
        """Prepend BASE <endpoint_root/> if the query has no BASE declaration.

        This ensures relative IRIs in GRAPH clauses (e.g. <ng-01.ttl>) resolve
        against the same root as the named graph URIs stored during bulk loading.
        """
        if re.search(r'\bBASE\b', query, re.IGNORECASE):
            return query
        base_uri = (
            f"http://{config.server_address}:{config.port}"
            f"/{DEFAULT_NAME}/"
        )
        return f"BASE <{base_uri}>\n{query}"

    def query(
        self,
        config: Config,
        query: str,
        result_format: str,
    ) -> tuple[int, str]:
        query = self._add_base_if_missing(config, query)
        return self._query(
            config,
            query,
            "query=",
            result_format,
            endpoint_suffix="/query",
        )

    def update(self, config: Config, query: str) -> tuple[int, str]:
        return self._query(
            config,
            query,
            "update=",
            "json",
            endpoint_suffix="/update",
        )

    def _query(
        self,
        config: Config,
        query: str,
        content_type: str,
        result_format: str,
        endpoint_suffix: str,
    ) -> tuple[int, str]:
        args = _make_args(
            config,
            accept=_get_accept_header(result_format),
            query=query,
            content_type=content_type,
            sparql_endpoint=(
                f"{config.server_address}:{config.port}"
                f"/{DEFAULT_NAME}{endpoint_suffix}"
            ),
        )
        try:
            with mute_log():
                qc = QueryCommand()
                qc.execute(args, called_from_conformance_test=True)
                query_output = str(qc.query_output)
                body, _, status_line = query_output.rpartition("HTTP_STATUS:")
                status_line = status_line.strip()
                if not status_line:
                    return 1, query_output
                status = int(status_line)
            return status, body
        except Exception as e:
            return 1, str(e)

    @staticmethod
    def _has_no_triples(graph_files: list[str]) -> bool:
        """Return True if all input files collectively contain zero RDF triples."""
        try:
            g = rdflib.ConjunctiveGraph()
            for f in graph_files:
                g.parse(f)
            return len(g) == 0
        except Exception:
            return False

    def _index(
        self,
        config: Config,
        graph_files: list[str],
    ) -> tuple[bool, str]:
        if not graph_files or self._has_no_triples(graph_files):
            # No triples to load — create the index directory so StartCommand's
            # presence check passes; Fuseki will initialize a fresh empty TDB2
            # store on startup.
            empty_index = Path("index/Data-0001")
            empty_index.mkdir(parents=True, exist_ok=True)
            (empty_index / ".keep").touch()
            return True, ""

        index_binary = "tdb2.xloader"
        if config.system == "native":
            index_binary = str(Path(config.path_to_binaries, index_binary))
        args = _make_args(
            config,
            input_files=" ".join(graph_files),
            index_binary=index_binary,
            threads=2,
            jvm_args="-Xms4G -Xmx4G",
            extra_args="",
            extra_env_args="",
        )
        try:
            with mute_log():
                result = IndexCommand().execute(
                    args=args, called_from_conformance_test=True
                )
        except Exception as e:
            return False, str(e)

        # tdb2.xloader crashes with "0 / 0: division by zero" when loading an
        # empty dataset (it computes a rate at the end). The index itself IS
        # created before that point, so we treat it as success if the index
        # directory exists.
        if not result and Path("index/Data-0001").exists():
            result = True

        index_log = _read_file(f"./{config.run_id}.index-log.txt")
        return result, index_log

    def _write_fuseki_config(self, config: Config) -> str:
        """Write a Fuseki config enabling path-based (direct-naming) GSP.

        Returns the path usable in the fuseki-server --conf argument (inside
        the Docker container for docker mode, or the local absolute path for
        native mode).
        """
        conf = (
            f'@prefix fuseki: <http://jena.apache.org/fuseki#> .\n'
            f'@prefix rdf:    <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .\n'
            f'@prefix tdb2:   <http://jena.apache.org/2016/tdb#> .\n\n'
            f'<#service> rdf:type fuseki:Service ;\n'
            f'    fuseki:name "{DEFAULT_NAME}" ;\n'
            f'    fuseki:endpoint [ fuseki:operation fuseki:query ;\n'
            f'                      fuseki:name "query" ] ;\n'
            f'    fuseki:endpoint [ fuseki:operation fuseki:query ;\n'
            f'                      fuseki:name "sparql" ] ;\n'
            f'    fuseki:endpoint [ fuseki:operation fuseki:update ;\n'
            f'                      fuseki:name "update" ] ;\n'
            f'    fuseki:endpoint [ fuseki:operation fuseki:gsp-rw ;\n'
            f'                      fuseki:name "data" ] ;\n'
            f'    fuseki:dataset <#dataset> ;\n'
            f'    .\n\n'
            f'<#dataset> rdf:type tdb2:DatasetTDB2 ;\n'
            f'    tdb2:location "index" ;\n'
            f'    .\n'
        )
        local_path = Path(os.getcwd()) / f"{config.run_id}-fuseki.ttl"
        local_path.write_text(conf, encoding="utf-8")
        if config.system != "native":
            return f"/opt/data/{config.run_id}-fuseki.ttl"
        return str(local_path)

    def _start_server(self, config: Config) -> tuple[bool, str]:
        server_binary = "fuseki-server"
        if config.system == "native":
            server_binary = str(Path(config.path_to_binaries, server_binary))
        conf_path = self._write_fuseki_config(config)
        args = _make_args(
            config,
            server_binary=server_binary,
            jvm_args="-Xms4G -Xmx4G",
            extra_env_args="",
            extra_args=f"--conf {conf_path}",
            run_in_foreground=False,
            timeout="60s",
        )
        try:
            with mute_log():
                result = StartCommand().execute(
                    args, called_from_conformance_test=True
                )
        except Exception as e:
            return False, str(e)

        server_log = _read_file(f"./{config.run_id}.server-log.txt")
        return result, server_log

    def _stop_server(self, config: Config) -> tuple[bool, str]:
        args = _make_args(
            config,
            cmdline_regex=StopCommand.DEFAULT_REGEX,
        )
        try:
            with mute_log(50):
                result = StopCommand().execute(args)
        except Exception as e:
            return False, str(e)
        return result, "Success"

    def _prepare_graphs(
        self,
        graph_paths: tuple[tuple[str, str], ...],
        config: Config,
    ) -> tuple[list[str], list[Path]]:
        workdir = Path(os.getcwd()).resolve()
        # rdflib resolves <> in data= strings against CWD + "/", so match that
        cwd_uri = workdir.as_uri() + "/"
        # Pre-pass: build a map from filename → HTTP named-graph URI for every
        # relative named-graph name.  When the same file is used as BOTH the
        # default graph and a named graph, <> in the default-graph data must
        # resolve to the stored named-graph URI (not the CWD) so that SPARQL
        # GRAPH variable bindings can match.
        file_to_named_uri: dict[str, str] = {}
        for gp, gn in graph_paths:
            if gn and gn != "-" and not has_uri_scheme(gn):
                fname = Path(gp).resolve().name
                file_to_named_uri[fname] = (
                    f"http://{config.server_address}:{config.port}"
                    f"/{DEFAULT_NAME}/{gn}"
                )
        graph_files: list[str] = []
        cleanup_paths: list[Path] = []
        for graph_path, graph_name in graph_paths:
            src = Path(graph_path).resolve()
            if graph_name and graph_name != "-":
                if src.suffix == ".rdf":
                    turtle_data = rdf_xml_to_turtle(str(src), graph_name)
                else:
                    turtle_data = src.read_text(encoding="utf-8")
                # For relative graph names (no URI scheme), resolve against
                # the Fuseki query endpoint URL so that SPARQL queries using
                # relative IRIs in GRAPH clauses resolve to the same URI.
                resolved_name = graph_name
                if not has_uri_scheme(graph_name):
                    resolved_name = (
                        f"http://{config.server_address}:{config.port}"
                        f"/{DEFAULT_NAME}/{graph_name}"
                    )
                trig_data = _graph_to_trig(turtle_data, resolved_name)
                graph_path_new = f"{src.stem}.trig"
                (workdir / graph_path_new).write_text(
                    trig_data, encoding="utf-8"
                )
                graph_files.append(graph_path_new)
                cleanup_paths.append(workdir / graph_path_new)
                continue
            if src.suffix == ".rdf":
                graph_path_new = f"{src.stem}.ttl"
                turtle_data = rdf_xml_to_turtle(str(src), graph_name)
                write_ttl_file(graph_path_new, turtle_data)
                graph_files.append(graph_path_new)
                cleanup_paths.append(workdir / graph_path_new)
                continue
            replacement = file_to_named_uri.get(src.name, cwd_uri)
            temp_name, temp_path = replace_empty_base_iri(src, workdir, replacement, "jena")
            if temp_path is not None:
                graph_files.append(temp_name)
                cleanup_paths.append(temp_path)
                continue
            if src.parent == workdir:
                graph_file = src.name
            else:
                graph_file = _copy_graph_to_workdir(str(src), str(workdir))
                cleanup_paths.append(workdir / src.name)
            graph_files.append(graph_file)
        return graph_files, cleanup_paths

    def _cleanup_graph_copies(self, cleanup_paths: list[Path]) -> None:
        for path in cleanup_paths:
            try:
                path.unlink()
            except FileNotFoundError:
                continue
