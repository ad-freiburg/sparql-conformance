#!/usr/bin/env python3
"""Backward-compatible entry point; the code lives in the
sparql_conformance package (see pyproject.toml). Prefer
`pip install -e .` and the `sparql-conformance` console script."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))

from sparql_conformance.main import main

if __name__ == "__main__":
    main()
