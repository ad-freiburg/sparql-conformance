# Writing a custom EngineManager

An `EngineManager` is the adapter between this test harness and a SPARQL engine. It's a single Python file that you pass to `--engine`. The harness dynamically loads the first `EngineManager` subclass it finds in that file — no registration needed.

## Quickstart

1. Copy the skeleton below into a new file, e.g. `my-engine-manager.py`.
2. Implement the five abstract methods (`setup`, `cleanup`, `query`, `update`, `protocol_endpoint`).
3. Run:
   ```bash
   sparql-conformance --engine ./my-engine-manager.py --name myrun --test-suites '{"sparql11":"/path/to/rdf-tests/sparql/sparql11"}'
   ```

## Skeleton

```python
import subprocess
import requests
import time
from typing import Tuple, Optional

from sparql_conformance.config import Config
from sparql_conformance.engines.engine_manager import EngineManager


class MyEngineManager(EngineManager):

    def setup(
        self,
        config: Config,
        graph_paths: Tuple[Tuple[str, str], ...],
    ) -> Tuple[bool, bool, str, str]:
        """
        Load data and start the engine.

        graph_paths is a tuple of (file_path, graph_name) pairs.
        graph_name is "-" for the default graph, or a URI string for named graphs.

        Returns: (index_success, server_success, index_log, server_log)
        """
        # 1. Build an index / load data from graph_paths
        # 2. Start the server on config.port
        # 3. Return success flags and log strings
        ...

    def cleanup(self, config: Config):
        """Stop the server and delete any temporary files."""
        ...

    def query(self, config: Config, query: str, result_format: str) -> Tuple[int, str]:
        """
        Execute a SPARQL SELECT / CONSTRUCT / ASK query.

        result_format is the wire-format token selected by the core, for
        example "srx" (SPARQL Results XML), "srj" (SPARQL Results JSON),
        "ttl", "csv", or "tsv". Return the requested wire format unchanged.
        For legacy SELECT/ASK tests whose expected result uses the RDF
        result-set vocabulary in Turtle, the core requests "srx" and performs
        the conversion itself.

        Returns: (http_status_code, response_body)
        """
        ...

    def update(self, config: Config, query: str) -> Tuple[int, str]:
        """
        Execute a SPARQL UPDATE query.

        Returns: (http_status_code, response_body)
        """
        ...

    def protocol_endpoint(self) -> str:
        """
        The path segment used for the SPARQL endpoint, e.g. "sparql".
        Protocol tests send requests to http://localhost:<port>/<protocol_endpoint>.
        """
        return "sparql"

    def graph_store_endpoint(self) -> str:
        """The engine's default Graph Store Protocol endpoint path."""
        return "sparql"
```

## The Config object

`config` is passed to every method and exposes:

| Attribute | Type | Description |
|---|---|---|
| `config.server_address` | `str` | Always `"localhost"` |
| `config.port` | `str` | Port from `--port` (default `"7001"`) |
| `config.path_to_binaries` | `str` | Absolute path from `--binaries-directory`; empty string if not set |
| `config.GRAPHSTORE` | `str` | Graph store endpoint path from `--graph-store`, or from `graph_store_endpoint()` when no override was given |
| `config.path_to_test_suite` | `str` | Absolute path to the test suite directory |
| `config.alias` | `list` | Type alias pairs from `--type-alias` |
| `config.exclude` | `list[str]` | Test/group names to skip |
| `config.include` | `list[str] \| None` | Test/group names to run (or `None` for all) |

## How `setup` is called

The harness groups tests by the set of RDF files they need. For each unique group, it calls `setup` once, runs all tests in that group, then calls `cleanup`. This cycle repeats for every group.

`graph_paths` always contains at least one entry. The graph name `"-"` means the default graph:

```python
# Single default graph
graph_paths = (("/path/to/data.ttl", "-"),)

# Default graph + one named graph
graph_paths = (
    ("/path/to/base.ttl", "-"),
    ("/path/to/named.ttl", "http://example.org/graph1"),
)
```

File formats you may receive: `.ttl`, `.nt`, `.nq`, `.trig`, `.rdf` (RDF/XML).

## A working example

[`rdflib_manager.py`](rdflib_manager.py) is a minimal, complete `EngineManager` that runs queries in-process via [rdflib](https://rdflib.readthedocs.io/) — no server, no docker. It only supports query/format/update/syntax tests (no protocol or graph-store-protocol, since those need a real HTTP server), but it is the smallest working reference for the five required methods. Try it out:

```bash
sparql-conformance --engine src/sparql_conformance/engines/rdflib_manager.py \
  --name rdflib-demo \
  --test-suites '{"sparql11":"/path/to/rdf-tests/sparql/sparql11"}' \
  --report summary
```

## Optional overrides

These methods have working defaults but can be overridden when needed.

### `protocol_update_endpoint() -> str`

If your engine exposes SPARQL UPDATE on a different path than SELECT, override this:

```python
def protocol_update_endpoint(self) -> str:
    return "sparql/update"  # default falls back to protocol_endpoint()
```

### `graph_store_endpoint() -> str`

Returns the engine's default Graph Store Protocol endpoint path. The default
implementation returns `"sparql"`; override it when the engine uses a different
route. Users can still replace the manager's value with `--graph-store`.

### `default_graph_construct_query() -> str`

Used by update tests to read back the default graph after a SPARQL UPDATE and compare it with the expected result. The default returns:

```sparql
CONSTRUCT {?s ?p ?o} WHERE { ?s ?p ?o }
```

Override this if your engine stores the default graph under a named IRI. Examples:

```python
# QLever: default graph lives at ql:default-graph
def default_graph_construct_query(self) -> str:
    return "CONSTRUCT {?s ?p ?o} WHERE { GRAPH ql:default-graph {?s ?p ?o}}"

# Blazegraph in quads mode: default graph is nullGraph
def default_graph_construct_query(self) -> str:
    return (
        "CONSTRUCT {?s ?p ?o} WHERE { "
        "GRAPH <http://www.bigdata.com/rdf#nullGraph> {?s ?p ?o}}"
    )
```

### `reset_graphs(config: Config, graph_paths: ...) -> bool`

Called between consecutive tests in the same graph group for **update** and **protocol** test types. The purpose is to restore the engine to the original graph state so each test starts clean — without the side-effects left by the previous test's UPDATE query.

The default implementation does a full `cleanup()` + `setup()`, which is always correct but restarts the server for every test. Override this when your engine supports a cheaper in-place reset:

```python
def reset_graphs(
    self,
    config: Config,
    graph_paths: Tuple[Tuple[str, str], ...],
) -> bool:
    # 1. Wipe all data
    status, _ = self.update(config, "CLEAR ALL")
    if not (200 <= status < 300):
        # Fall back to full restart on failure
        self.cleanup(config)
        ok_i, ok_s, _, _ = self.setup(config, graph_paths)
        return ok_i and ok_s

    # 2. Re-upload each graph via Graph Store HTTP PUT
    for graph_path, graph_name in graph_paths:
        ttl = read_file(graph_path)  # load/convert as needed
        params = {"default": ""} if graph_name == "-" else {"graph": graph_name}
        r = requests.put(
            f"http://{config.server_address}:{config.port}/sparql",
            params=params,
            data=ttl.encode("utf-8"),
            headers={"Content-Type": "text/turtle"},
        )
        if not (200 <= r.status_code < 300):
            self.cleanup(config)
            ok_i, ok_s, _, _ = self.setup(config, graph_paths)
            return ok_i and ok_s

    return True
```

Returning `False` causes the harness to mark all remaining tests in the group as FAILED with a server error.

### `supported_graphstore_features() -> Set[str]`

Graph Store Protocol tests can declare requirements via `mf:requires` (e.g. needing the graph store to support direct or indirect graph identification, or graph creation via `POST`). Return the subset your engine supports; a test requiring an unsupported feature is skipped (reported as an intended deviation) instead of run and failed. Default assumes full support:

```python
from sparql_conformance.engines.engine_manager import ALL_GRAPHSTORE_FEATURES

def supported_graphstore_features(self) -> set:
    return ALL_GRAPHSTORE_FEATURES - {"POSTGraphCreation"}
```

### `activate_syntax_test_mode(config: Config)`

Called before syntax tests if your engine needs a special mode to return error responses for invalid queries rather than silently accepting them. Default implementation does nothing.

### `get_server_log(config: Config) -> str`

Called after each test group; the returned log is attached to the group's test results (empty string for "no log"). The default reads `./<config.run_id>.server-log.txt`, which is where the built-in managers write it. Override this if your engine logs somewhere else.
