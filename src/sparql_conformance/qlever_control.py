from __future__ import annotations

import sys
from typing import TextIO


QLEVER_CONTROL_BRANCH = "sparql-conformance-command-all-engines"
QLEVER_CONTROL_REPOSITORY = "https://github.com/SIRDNARch/qlever-control.git"
QLEVER_CONTROL_MODULES = (
    "qlever",
    "qblazegraph",
    "qgraphdb",
    "qjena",
    "qmdb",
    "qoxigraph",
    "qvirtuoso",
)


class QleverControlRequiredError(RuntimeError):
    """Raised when an operation needs the optional qlever-control package."""


def is_qlever_control_import_error(error: ImportError) -> bool:
    """Return whether an import error refers to a qlever-control module."""
    module_name = getattr(error, "name", None)
    if not module_name:
        return False
    return any(
        module_name == prefix or module_name.startswith(f"{prefix}.")
        for prefix in QLEVER_CONTROL_MODULES
    )


def installation_message(operation: str | None = None) -> str:
    """Return the actionable message for an unavailable integration."""
    heading = (
        f"{operation} requires qlever-control."
        if operation
        else "This operation requires qlever-control."
    )
    return (
        f"{heading}\n\n"
        "For local development, install both checkouts in editable mode "
        "(qlever-control first):\n\n"
        "  python -m pip install -e /path/to/qlever-control\n"
        "  python -m pip install -e /path/to/sparql-conformance\n\n"
        "Or install qlever-control from branch "
        f"`{QLEVER_CONTROL_BRANCH}`:\n\n"
        "  python -m pip install \\\n"
        f'    "git+{QLEVER_CONTROL_REPOSITORY}@{QLEVER_CONTROL_BRANCH}"'
    )


def print_installation_message(
    operation: str | None = None,
    *,
    file: TextIO = sys.stderr,
) -> None:
    print(installation_message(operation), file=file)
