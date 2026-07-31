"""Tests for the optional qlever-control integration boundary."""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from sparql_conformance.main import load_engine_from_file
from sparql_conformance.qlever_control import QLEVER_CONTROL_BRANCH


REPO_ROOT = Path(__file__).parent.parent
SOURCE_ROOT = REPO_ROOT / "src"

BLOCK_QLEVER_CONTROL = """
import importlib.abc
import sys

PREFIXES = (
    "qlever",
    "qblazegraph",
    "qgraphdb",
    "qjena",
    "qmdb",
    "qoxigraph",
    "qvirtuoso",
)

class BlockQleverControl(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if any(
            fullname == prefix or fullname.startswith(prefix + ".")
            for prefix in PREFIXES
        ):
            raise ModuleNotFoundError(
                "blocked qlever-control import: " + fullname,
                name=fullname,
            )
        return None

sys.meta_path.insert(0, BlockQleverControl())
"""


def isolated_environment(tmp_path: Path) -> dict[str, str]:
    """Return an environment in which qlever-control cannot be imported."""
    (tmp_path / "sitecustomize.py").write_text(BLOCK_QLEVER_CONTROL)
    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join((str(tmp_path), str(SOURCE_ROOT)))
    return env


def run_module(
    module: str,
    *arguments: str,
    env: dict[str, str],
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", module, *arguments],
        cwd=REPO_ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


def write_minimal_suite(directory: Path) -> None:
    directory.mkdir()
    (directory / "manifest.ttl").write_text(
        """
@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix mf: <http://www.w3.org/2001/sw/DataAccess/tests/test-manifest#> .
@prefix : <manifest#> .

<> rdf:type mf:Manifest ;
   mf:entries ( :syntax ) .

:syntax rdf:type mf:PositiveSyntaxTest11 ;
        mf:name "syntax" ;
        mf:action <syntax.rq> .
"""
    )
    (directory / "syntax.rq").write_text("SELECT * WHERE { ?s ?p ?o }\n")


def write_minimal_manager(path: Path) -> None:
    path.write_text(
        """
from sparql_conformance.engines.engine_manager import EngineManager

class MinimalManager(EngineManager):
    def setup(self, config, graph_paths):
        return True, True, "", ""

    def cleanup(self, config):
        pass

    def query(self, config, query, result_format):
        return 200, ""

    def update(self, config, query):
        return 200, ""

    def protocol_endpoint(self):
        return "sparql"
"""
    )


def test_file_based_manager_runs_without_qlever_control(tmp_path):
    suite = tmp_path / "suite"
    manager = tmp_path / "manager.py"
    results = tmp_path / "results"
    write_minimal_suite(suite)
    write_minimal_manager(manager)

    result = run_module(
        "sparql_conformance.main",
        "--engine",
        str(manager),
        "--name",
        "standalone",
        "--results-dir",
        str(results),
        "--test-suites",
        json.dumps({"minimal": str(suite)}),
        env=isolated_environment(tmp_path),
    )

    assert result.returncode == 0, result.stderr
    assert (results / "standalone.json.bz2").is_file()


def test_named_engine_prints_qlever_control_installation_hint(tmp_path):
    suite = tmp_path / "suite"
    suite.mkdir()

    result = run_module(
        "sparql_conformance.main",
        "--engine",
        "qlever",
        "--name",
        "named",
        "--test-suites",
        json.dumps({"minimal": str(suite)}),
        env=isolated_environment(tmp_path),
    )

    assert result.returncode == 1
    assert "Engine `qlever` requires qlever-control" in result.stderr
    assert "pip install -e /path/to/qlever-control" in result.stderr
    assert QLEVER_CONTROL_BRANCH in result.stderr


def test_integrated_cli_prints_qlever_control_installation_hint(tmp_path):
    result = run_module(
        "sparql_conformance.integrated_main",
        "--help",
        env=isolated_environment(tmp_path),
    )

    assert result.returncode == 1
    assert "The `sparql_conformance` command requires qlever-control" in result.stderr
    assert QLEVER_CONTROL_BRANCH in result.stderr


def test_package_module_runs_integrated_cli(tmp_path):
    result = run_module(
        "sparql_conformance",
        "visualize",
        "--help",
        env=isolated_environment(tmp_path),
    )

    assert result.returncode == 1
    assert "The `sparql_conformance` command requires qlever-control" in result.stderr
    assert QLEVER_CONTROL_BRANCH in result.stderr


def test_integrated_cli_rejects_incompatible_qlever_control(tmp_path):
    qlever = tmp_path / "qlever"
    qlever.mkdir()
    (qlever / "__init__.py").write_text("command_objects = {}\n")
    (qlever / "qlever_main.py").write_text(
        "def main():\n"
        "    raise AssertionError('incompatible qlever-control was executed')\n"
    )
    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join((str(tmp_path), str(SOURCE_ROOT)))

    result = run_module(
        "sparql_conformance.integrated_main",
        "--help",
        env=env,
    )

    assert result.returncode == 1
    assert "The `sparql_conformance` command requires qlever-control" in result.stderr
    assert QLEVER_CONTROL_BRANCH in result.stderr


def test_custom_manager_that_imports_qlever_control_is_gated(tmp_path):
    suite = tmp_path / "suite"
    suite.mkdir()
    manager = tmp_path / "manager.py"
    manager.write_text("from qlever.command import QleverCommand\n")

    result = run_module(
        "sparql_conformance.main",
        "--engine",
        str(manager),
        "--name",
        "custom",
        "--test-suites",
        json.dumps({"minimal": str(suite)}),
        env=isolated_environment(tmp_path),
    )

    assert result.returncode == 1
    assert f"Engine manager `{manager}` requires qlever-control" in result.stderr
    assert QLEVER_CONTROL_BRANCH in result.stderr


def test_missing_manager_file_is_reported_as_a_path_error(tmp_path):
    suite = tmp_path / "suite"
    suite.mkdir()
    manager = tmp_path / "missing-manager.py"

    result = run_module(
        "sparql_conformance.main",
        "--engine",
        str(manager),
        "--name",
        "missing",
        "--test-suites",
        json.dumps({"minimal": str(suite)}),
        env=isolated_environment(tmp_path),
    )

    assert result.returncode == 2
    assert f"Engine manager file not found: {manager}" in result.stderr


def test_file_without_engine_manager_is_rejected(tmp_path):
    manager = tmp_path / "manager.py"
    manager.write_text("VALUE = 42\n")

    with pytest.raises(ValueError, match="No EngineManager subclass found"):
        load_engine_from_file(str(manager))


def test_unrelated_custom_manager_import_error_is_not_relabelled(tmp_path):
    manager = tmp_path / "manager.py"
    manager.write_text("import dependency_that_does_not_exist\n")

    with pytest.raises(
        ModuleNotFoundError,
        match="dependency_that_does_not_exist",
    ):
        load_engine_from_file(str(manager))
