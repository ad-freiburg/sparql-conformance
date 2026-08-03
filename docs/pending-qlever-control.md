# Temporary qlever-control branch installation

Use this guide while the required qlever-control changes remain on the
[`SIRDNARch/sparql-conformance-command-all-engines` branch](https://github.com/SIRDNARch/qlever-control/tree/sparql-conformance-command-all-engines).
Delete this guide and update the main installation instructions when those
changes are available from qlever-control's default branch or a release.

For commands and supported engines, see the
[integrated CLI reference](integrated.md).

## Prerequisites

- Git
- Python 3.10 or newer
- A running Docker or Podman service

## Install both repositories

```bash
mkdir sparql-conformance-work
cd sparql-conformance-work

python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip

git clone https://github.com/SIRDNARch/qlever-control.git
git -C qlever-control switch sparql-conformance-command-all-engines

git clone https://github.com/ad-freiburg/sparql-conformance.git

python -m pip install -e ./qlever-control
python -m pip install -e ./sparql-conformance
```

Install qlever-control first. `sparql-conformance` owns the
`sparql_conformance` executable and must be installed last, particularly when
upgrading from an older qlever-control revision that installed an executable
with the same name.

Verify both CLIs:

```bash
qlever --help
sparql-conformance --help
sparql_conformance --help
```

The hyphenated command is the standalone runner. The underscored command is the
Qleverfile-based integration. Continue with the
[built-in engine quickstart](../README.md#quickstart-with-a-built-in-engine).
