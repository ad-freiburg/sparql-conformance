"""Factory for the built-in engine managers.

The concrete managers depend on qlever-control (qlever, qblazegraph, qjena,
...), so they are imported lazily: the core package stays importable without
qlever-control, and only actually using a built-in engine requires it.
"""

import importlib

from sparql_conformance.qlever_control import (
    QleverControlRequiredError,
    is_qlever_control_import_error,
    installation_message,
)

_MANAGERS = {
    "qlever": ("sparql_conformance.engines.qlever", "QLeverManager"),
    "qlever-binaries": ("sparql_conformance.engines.qlever", "QLeverManager"),
    "blazegraph": (
        "sparql_conformance.engines.blazegraph_manager",
        "BlazegraphManager",
    ),
    "graphdb": (
        "sparql_conformance.engines.graphdb_manager",
        "GraphdbManager",
    ),
    "jena": ("sparql_conformance.engines.jena_manager", "JenaManager"),
    "mdb": ("sparql_conformance.engines.mdb_manager", "MdbManager"),
    "oxigraph": (
        "sparql_conformance.engines.oxigraph_manager",
        "OxigraphManager",
    ),
    "virtuoso": (
        "sparql_conformance.engines.virtuoso_manager",
        "VirtuosoManager",
    ),
}

ENGINE_TYPES = list(_MANAGERS)


def get_engine_manager(engine_type: str):
    """Get the appropriate engine manager for the given engine type."""
    entry = _MANAGERS.get(engine_type)
    if entry is None:
        raise ValueError(f"Unsupported engine type: {engine_type}")
    module_name, class_name = entry
    try:
        module = importlib.import_module(module_name)
    except ImportError as error:
        if is_qlever_control_import_error(error):
            raise QleverControlRequiredError(
                installation_message(f"Engine `{engine_type}`")
            ) from error
        raise
    return getattr(module, class_name)()
