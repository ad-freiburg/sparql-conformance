import argparse
import importlib.util
import json
import os

from sparql_conformance.config import Config
from sparql_conformance.engines import get_engine_manager
from sparql_conformance.engines.engine_manager import EngineManager
from sparql_conformance.qlever_control import (
    QleverControlRequiredError,
    is_qlever_control_import_error,
    installation_message,
)
from sparql_conformance.runner import (
    assemble_suites,
    parse_test_suites,
    run_suites,
)

try:
    from qlever.log import log
except ImportError:
    import logging
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    log = logging.getLogger(__name__)


def load_engine_from_file(path: str) -> EngineManager:
    """Dynamically load the first EngineManager subclass found in a Python file."""
    abs_path = os.path.abspath(path)
    spec = importlib.util.spec_from_file_location("engine_module", abs_path)
    if spec is None or spec.loader is None:
        raise ValueError(f"Cannot load module from {path}")
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except ImportError as error:
        if is_qlever_control_import_error(error):
            raise QleverControlRequiredError(
                installation_message(f"Engine manager `{path}`")
            ) from error
        raise
    for name in dir(module):
        obj = getattr(module, name)
        if (
            isinstance(obj, type)
            and issubclass(obj, EngineManager)
            and obj is not EngineManager
        ):
            return obj()
    raise ValueError(f"No EngineManager subclass found in {path}")


def get_engine_manager_by_name(name: str) -> EngineManager:
    """Resolve a named engine type (the built-in managers require qlever-control)."""
    return get_engine_manager(name)


def looks_like_file_path(value: str) -> bool:
    """Return whether an engine argument was intended as a file path."""
    return (
        value.endswith(".py")
        or value.startswith(".")
        or os.sep in value
        or (os.altsep is not None and os.altsep in value)
    )


def main():
    parser = argparse.ArgumentParser(
        description="Run SPARQL conformance tests against a SPARQL engine.",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "--engine",
        required=True,
        metavar="FILE_OR_TYPE",
        help=(
            "Path to a Python file containing an EngineManager subclass, "
            "or a named engine type (requires qlever-control).\n"
            "Example: --engine ./qlever-binaries-manager.py"
        ),
    )
    parser.add_argument(
        "--name",
        required=True,
        help="Name for this run; used as the output filename: <results-dir>/<name>.json.bz2",
    )
    parser.add_argument(
        "--results-dir",
        default="./results",
        dest="results_dir",
        help="Directory for the output JSON file (default: ./results).",
    )
    parser.add_argument(
        "--port",
        default="7001",
        help="Port for the SPARQL server (default: 7001)",
    )
    parser.add_argument(
        "--graph-store",
        default=None,
        dest="graph_store",
        help=(
            "Override the engine manager's graph store endpoint for graph "
            "store protocol tests"
        ),
    )
    parser.add_argument(
        "--test-suites",
        required=True,
        dest="test_suites",
        type=parse_test_suites,
        metavar="SUITE_TO_DIR_JSON",
        help=(
            "JSON object mapping suite names to directories.\n"
            "Example: --test-suites "
            '\'{"sparql11": "/path/to/sparql11", '
            '"my-suite": "/path/to/custom"}\''
        ),
    )
    parser.add_argument(
        "--binaries-directory",
        default="",
        dest="binaries_directory",
        help="Directory containing qlever binaries (used by file-based engine managers).",
    )
    parser.add_argument(
        "--server-binary",
        default="qlever-server",
        dest="server_binary",
        help="Name of the QLever server binary (default: qlever-server).",
    )
    parser.add_argument(
        "--index-binary",
        default="qlever-index",
        dest="index_binary",
        help="Name of the QLever index builder binary (default: qlever-index).",
    )
    parser.add_argument(
        "--exclude",
        default=[],
        type=lambda s: s.split(","),
        help="Comma-separated list of test names or groups to exclude.",
    )
    parser.add_argument(
        "--include",
        default=None,
        type=lambda s: s.split(","),
        help="Comma-separated list of test names or groups to include.",
    )
    parser.add_argument(
        "--type-alias",
        default=None,
        dest="type_alias",
        type=json.loads,
        help=(
            "JSON list of type pairs considered as intended deviations.\n"
            "Example: --type-alias "
            '\'[["http://www.w3.org/2001/XMLSchema#integer",'
            '"http://www.w3.org/2001/XMLSchema#int"]]\''
        ),
    )
    parser.add_argument(
        "--report",
        default="none",
        choices=["none", "summary", "line"],
        help=(
            "Console output verbosity (default: none, only the JSON is written):\n"
            "  none    - unchanged, no extra console output\n"
            "  summary - end-of-run totals plus a list of failed tests\n"
            "  line    - a live PASS/FAIL line per test, plus the summary"
        ),
    )
    parser.add_argument(
        "--compare-to",
        default=None,
        dest="compare_to",
        metavar="RESULTS_FILE",
        help=(
            "Path to a previous <name>.json.bz2 run to compare against; prints "
            "regressions (newly failing) and fixes (newly passing) at the end."
        ),
    )

    args = parser.parse_args()

    active_suites = assemble_suites(args.test_suites)

    for suite_name, d in active_suites:
        if not os.path.isdir(d):
            parser.error(f"Test suite {suite_name!r} directory not found: {d}")

    try:
        if os.path.isfile(args.engine):
            engine_manager = load_engine_from_file(args.engine)
        elif looks_like_file_path(args.engine):
            parser.error(f"Engine manager file not found: {args.engine}")
        else:
            engine_manager = get_engine_manager_by_name(args.engine)
    except QleverControlRequiredError as error:
        parser.exit(1, f"{error}\n")
    except ValueError as error:
        parser.error(str(error))

    alias = [tuple(x) for x in args.type_alias] if args.type_alias else []

    def make_config(suite_dir):
        return Config(
            image=None,
            system="native",
            port=args.port,
            graph_store=args.graph_store,
            testsuite_dir=suite_dir,
            type_alias=alias,
            binaries_directory=args.binaries_directory,
            exclude=args.exclude,
            include=args.include,
            server_binary=args.server_binary,
            index_binary=args.index_binary,
        )

    run_suites(
        active_suites,
        make_config,
        lambda: engine_manager,
        name=args.name,
        results_dir=args.results_dir,
        report_mode=args.report,
        compare_to=args.compare_to,
    )


if __name__ == "__main__":
    main()
