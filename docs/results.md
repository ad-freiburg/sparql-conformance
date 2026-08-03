# Result file format and status meanings

Each run writes `<results-dir>/<name>.json.bz2`. The file contains UTF-8 JSON
compressed with bzip2. New results use format version 2, which combines any
number of named test suites in one document.

## Version 2 structure

The following example shows the stable top-level shape and representative test
fields. Actual test entries contain additional diagnostics and source data.

```json
{
  "version": 2,
  "suites": {
    "sparql11": {
      "tests": {
        "Example test": {
          "test": "https://example.org/manifest#test",
          "typeName": "QueryEvaluationTest",
          "name": "Example test",
          "group": "basic",
          "status": "Passed",
          "errorType": "",
          "executionQuery": "SELECT * WHERE { ?s ?p ?o }",
          "datasetSources": []
        }
      },
      "info": {
        "passed": 1,
        "tests": 1,
        "failed": 0,
        "passedFailed": 0,
        "notTested": 0
      }
    }
  },
  "info": {
    "name": "info",
    "passed": 1,
    "tests": 1,
    "failed": 0,
    "passedFailed": 0,
    "notTested": 0
  }
}
```

`suites` is keyed by the names supplied through `--test-suites`. Each suite
contains its test entries and a summary. The top-level `info` object contains
the totals across all suites. The historical `passedFailed` field counts
intended deviations.

Test entries include manifest metadata, the query and graph inputs, execution
diagnostics, engine logs, and expected/actual output. Fields such as
`expectedHtml`, `gotHtml`, `expectedHtmlRed`, and `gotHtmlRed` are
display-oriented HTML used by the result viewer.

Consumers should check `version`, ignore unknown test fields, and treat a
missing `version` as the legacy single-suite format. The `--compare-to` command
expects version 2 results and matches tests by suite key and test name.

## Status values

| Status | Meaning |
|---|---|
| `Passed` | The engine response matched the expected W3C test result. |
| `Failed` | The response, protocol behavior, engine setup, or result format did not match. Consult `errorType` and the diagnostic fields. |
| `Intended deviation` | A known, explicitly accepted deviation applied, such as a configured datatype equivalence or an unsupported declared Graph Store feature. It is not a standards-conforming pass. |
| `Not tested` | The harness did not execute the test, for example because the test category is not implemented. |

Console output abbreviates intended deviations as `INTD`. Summary objects use
`passed`, `failed`, `passedFailed`, and `notTested` for the four statuses.

## Current limitations

- Service Description tests are recorded as `Not tested`; the harness does not
  currently execute them.
- The bundled rdflib adapter has no HTTP server and therefore does not run
  SPARQL Protocol or Graph Store Protocol tests.
- Built-in Qleverfiles configure engine-specific datatype aliases. These can
  turn an otherwise failing comparison into an `Intended deviation`; review
  the selected Qleverfile when interpreting results.
- A Graph Store Protocol test whose `mf:requires` features are not supported by
  the engine is recorded as an `Intended deviation` rather than executed.
- The built-in engine integration currently depends on a pending qlever-control
  branch; see the [temporary installation guide](pending-qlever-control.md).
