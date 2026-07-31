"""Shared suite helpers used by the standalone CLI and qlever-control."""

import argparse
import json
import os

from sparql_conformance import console_report
from sparql_conformance.extract_tests import extract_tests
from sparql_conformance.testsuite import TestSuite


def parse_test_suites(value: str) -> dict[str, str]:
    """Parse a JSON object mapping test-suite names to directories."""
    duplicate_keys = []

    def object_from_pairs(pairs):
        result = {}
        for key, directory in pairs:
            if key in result:
                duplicate_keys.append(key)
            result[key] = directory
        return result

    try:
        test_suites = json.loads(value, object_pairs_hook=object_from_pairs)
    except (TypeError, ValueError) as error:
        raise argparse.ArgumentTypeError(f"invalid JSON: {error}") from error

    if not isinstance(test_suites, dict):
        raise argparse.ArgumentTypeError(
            "must be a JSON object mapping suite names to directories"
        )
    if duplicate_keys:
        duplicates = ", ".join(repr(key) for key in duplicate_keys)
        raise argparse.ArgumentTypeError(f"duplicate suite name(s): {duplicates}")
    if not test_suites:
        raise argparse.ArgumentTypeError("must contain at least one test suite")

    for name, directory in test_suites.items():
        if not name.strip():
            raise argparse.ArgumentTypeError("suite names must not be blank")
        if not isinstance(directory, str):
            raise argparse.ArgumentTypeError(
                f"directory for suite {name!r} must be a string"
            )
        if not directory.strip():
            raise argparse.ArgumentTypeError(
                f"directory for suite {name!r} must not be blank"
            )
    return test_suites


def assemble_suites(test_suites):
    """Build the ordered list of (suite_key, directory) pairs to run."""
    return list(test_suites.items())


def run_suites(active_suites, make_config, make_engine_manager, name,
               results_dir, report_mode, compare_to=None):
    """Run each suite and write one combined v2 result file.

    Parameters:
        active_suites: list of (suite_key, suite_dir) pairs (non-empty).
        make_config: callable(suite_dir) -> Config for that suite.
        make_engine_manager: callable() -> EngineManager, invoked per suite.
        name: run name; the output file is <results_dir>/<name>.json.bz2.
        results_dir: directory for the output file.
        report_mode: "none", "summary" or "line".
        compare_to: optional path to a previous run to diff against.

    Returns the v2 results dict that was written.
    """
    suites_data = {}
    total_info = {
        "passed": 0,
        "tests": 0,
        "failed": 0,
        "passedFailed": 0,
        "notTested": 0,
    }
    last_suite = None

    for suite_key, suite_dir in active_suites:
        print(f"Running suite '{suite_key}' from {suite_dir}...")
        config = make_config(suite_dir)
        tests, test_count = extract_tests(config)
        suite = TestSuite(
            name=name,
            tests=tests,
            test_count=test_count,
            config=config,
            engine_manager=make_engine_manager(),
            results_dir=results_dir,
            report_mode=report_mode,
        )
        suite.run()
        tests_dict, info_dict = suite.build_results_dict()
        suites_data[suite_key] = {"tests": tests_dict, "info": info_dict}
        for key in total_info:
            total_info[key] += info_dict[key]
        last_suite = suite

    output = {
        "version": 2,
        "suites": suites_data,
        "info": {"name": "info", **total_info},
    }

    os.makedirs(results_dir, exist_ok=True)
    last_suite.compress_json_bz2(
        output, os.path.join(results_dir, f"{name}.json.bz2")
    )
    print("Finished!")

    if report_mode != "none":
        console_report.print_summary(total_info, suites_data)
        console_report.print_failures(suites_data)

    if compare_to:
        baseline = console_report.read_json_bz2(compare_to)
        console_report.print_comparison(
            console_report.compare_runs(baseline, output)
        )

    return output
