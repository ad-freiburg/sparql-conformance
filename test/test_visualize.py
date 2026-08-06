"""Regression tests for the integrated visualization deployment."""

import importlib
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace


COMPOSE_FILE = (
    Path(__file__).parent.parent
    / "src"
    / "sparql_conformance"
    / "docker-compose.yml"
)


def test_visualize_compose_matches_private_ui_contract():
    compose = COMPOSE_FILE.read_text()

    assert "https://github.com/ad-freiburg/sparql-conformance-ui.git" in compose
    assert "web-private:" in compose
    assert "api-private:" in compose
    assert "API_SURFACE: all" in compose
    assert "DB_PATH: /tmp/conformance.db" in compose
    assert "db_data" not in compose


def test_visualize_compose_uses_selected_ui_branch_for_both_images():
    compose = COMPOSE_FILE.read_text()

    context = (
        "https://github.com/ad-freiburg/sparql-conformance-ui.git"
        "#${SPARQL_CONFORMANCE_UI_BRANCH:-main}"
    )
    assert compose.count(context) == 2
    assert compose.count("${SPARQL_CONFORMANCE_UI_BRANCH:-main}") == 2
    assert compose.count("${SPARQL_CONFORMANCE_UI_IMAGE_TAG:-main}") == 2


def _load_visualize_module(monkeypatch):
    qlever = ModuleType("qlever")
    command = ModuleType("qlever.command")
    command.QleverCommand = object
    log_module = ModuleType("qlever.log")
    log_module.log = SimpleNamespace(
        info=lambda message: None,
        error=lambda message: None,
    )
    util = ModuleType("qlever.util")
    util.run_command = lambda *args, **kwargs: None

    monkeypatch.setitem(sys.modules, "qlever", qlever)
    monkeypatch.setitem(sys.modules, "qlever.command", command)
    monkeypatch.setitem(sys.modules, "qlever.log", log_module)
    monkeypatch.setitem(sys.modules, "qlever.util", util)
    monkeypatch.delitem(
        sys.modules,
        "sparql_conformance.commands.visualize",
        raising=False,
    )
    module = importlib.import_module("sparql_conformance.commands.visualize")
    # Avoid leaving a module backed by the fake qlever package in sys.modules.
    sys.modules.pop("sparql_conformance.commands.visualize", None)
    return module


def test_visualize_refreshes_branch_and_uses_safe_image_tag(monkeypatch, tmp_path):
    visualize = _load_visualize_module(monkeypatch)
    calls = []
    monkeypatch.setattr(
        visualize,
        "run_command",
        lambda command, **kwargs: calls.append((command, kwargs)),
    )

    args = SimpleNamespace(
        system="docker",
        result_directory=str(tmp_path),
        port="3100",
        ui_branch="feat/service-endpoint-fixtures",
    )

    assert visualize.VisualizeCommand().execute(args)
    assert len(calls) == 4
    assert calls[0][0].endswith(" down")
    assert calls[1][0].endswith(" build --pull")
    assert calls[2][0].endswith(" up")
    assert calls[3][0].endswith(" down")
    build_command = calls[1][0]
    assert "SPARQL_CONFORMANCE_UI_BRANCH=feat/service-endpoint-fixtures" in build_command
    assert (
        "SPARQL_CONFORMANCE_UI_IMAGE_TAG=feat-service-endpoint-fixtures-"
        in build_command
    )
