"""Tests for JSON-based test-suite configuration."""

import argparse
import configparser
import os
from pathlib import Path
import subprocess
import sys
from types import ModuleType

import pytest

from sparql_conformance.qleverfile import qleverfile_args
from sparql_conformance.runner import assemble_suites, parse_test_suites


REPO_ROOT = Path(__file__).parent.parent
QLEVERFILES = REPO_ROOT / "src" / "sparql_conformance" / "Qleverfiles"


def test_parse_test_suites_preserves_order():
    value = '{"sparql11": "./11", "sparql10": "./10", "vendor": "./v"}'

    parsed = parse_test_suites(value)

    assert assemble_suites(parsed) == [
        ("sparql11", "./11"),
        ("sparql10", "./10"),
        ("vendor", "./v"),
    ]


@pytest.mark.parametrize(
    ("value", "message"),
    [
        ("not-json", "invalid JSON"),
        ("null", "must be a JSON object"),
        ("[]", "must be a JSON object"),
        ('"./suite"', "must be a JSON object"),
        ("{}", "must contain at least one test suite"),
        ('{"suite": "./one", "suite": "./two"}', "duplicate suite name"),
        ('{"": "./suite"}', "suite names must not be blank"),
        ('{"   ": "./suite"}', "suite names must not be blank"),
        ('{"suite": null}', "must be a string"),
        ('{"suite": 123}', "must be a string"),
        ('{"suite": ""}', "must not be blank"),
        ('{"suite": "   "}', "must not be blank"),
    ],
)
def test_parse_test_suites_rejects_invalid_values(value, message):
    with pytest.raises(argparse.ArgumentTypeError, match=message):
        parse_test_suites(value)


def test_qleverfile_argument_uses_shared_parser(monkeypatch):
    qvirtuoso = ModuleType("qvirtuoso")
    commands = ModuleType("qvirtuoso.commands")
    setup_config = ModuleType("qvirtuoso.commands.setup_config")

    class SetupConfigCommand:
        IMAGE = "virtuoso:test"

    setup_config.SetupConfigCommand = SetupConfigCommand
    monkeypatch.setitem(sys.modules, "qvirtuoso", qvirtuoso)
    monkeypatch.setitem(sys.modules, "qvirtuoso.commands", commands)
    monkeypatch.setitem(sys.modules, "qvirtuoso.commands.setup_config", setup_config)
    all_args = {}

    qleverfile_args(all_args)

    positional, keyword = all_args["conformance"]["test_suites"]
    assert positional == ("--test-suites",)
    assert keyword["required"] is True
    assert keyword["type"] is parse_test_suites
    assert "testsuite_dir" not in all_args["conformance"]
    assert "sparql11_dir" not in all_args["conformance"]
    assert "sparql10_dir" not in all_args["conformance"]
    assert "custom" not in all_args["conformance"]

    _, graph_store_keyword = all_args["conformance"]["graph_store"]
    assert graph_store_keyword["required"] is False
    assert graph_store_keyword["default"] is None


@pytest.mark.parametrize("qleverfile", sorted(QLEVERFILES.glob("Qleverfile.*")))
def test_bundled_qleverfile_has_valid_test_suites(qleverfile):
    config = configparser.ConfigParser(interpolation=None)
    config.read(qleverfile)

    parsed = parse_test_suites(config["conformance"]["TEST_SUITES"])

    assert parsed == {
        "sparql11": "./testsuite-files/sparql/sparql11/",
        "sparql10": "./testsuite-files/sparql/sparql10/",
    }
    assert "SPARQL11_DIR" not in config["conformance"]
    assert "SPARQL10_DIR" not in config["conformance"]
    assert "GRAPH_STORE" not in config["conformance"]


def run_cli(*arguments):
    env = os.environ.copy()
    env["PYTHONPATH"] = str(REPO_ROOT / "src")
    return subprocess.run(
        [sys.executable, "-m", "sparql_conformance.main", *arguments],
        cwd=REPO_ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


def test_standalone_help_exposes_only_test_suites_argument():
    result = run_cli("--help")

    assert result.returncode == 0
    assert "--test-suites" in result.stdout
    assert "--sparql11-dir" not in result.stdout
    assert "--sparql10-dir" not in result.stdout
    assert "--custom" not in result.stdout


def test_standalone_cli_requires_test_suites():
    result = run_cli("--engine", "unused", "--name", "test")

    assert result.returncode == 2
    assert "the following arguments are required: --test-suites" in result.stderr


def test_standalone_cli_rejects_old_suite_arguments():
    result = run_cli(
        "--engine",
        "unused",
        "--name",
        "test",
        "--test-suites",
        '{"suite": "./does-not-exist"}',
        "--sparql11-dir",
        "./suite",
    )

    assert result.returncode == 2
    assert "--sparql11-dir" in result.stderr


def test_standalone_cli_names_missing_suite_directory():
    result = run_cli(
        "--engine",
        "unused",
        "--name",
        "test",
        "--test-suites",
        '{"vendor": "./does-not-exist"}',
    )

    assert result.returncode == 2
    assert "Test suite 'vendor' directory not found" in result.stderr
