from __future__ import annotations

import sys

from sparql_conformance.qlever_control import (
    is_qlever_control_import_error,
    print_installation_message,
)

INTEGRATED_COMMANDS = {"analyze", "setup", "test", "visualize"}


def main() -> None:
    """Run the qlever-control-integrated command-line interface."""
    sys.argv[0] = "sparql_conformance"
    try:
        from qlever import command_objects
        from qlever.qlever_main import main as qlever_main
    except ImportError as error:
        if is_qlever_control_import_error(error):
            print_installation_message("The `sparql_conformance` command")
            raise SystemExit(1) from error
        raise
    if not INTEGRATED_COMMANDS.issubset(command_objects):
        print_installation_message("The `sparql_conformance` command")
        raise SystemExit(1)
    qlever_main()


if __name__ == "__main__":
    main()
