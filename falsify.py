#!/usr/bin/env python3
"""Falsification Engine — pre-registration + CI for AI-agent claims."""

from __future__ import annotations

import argparse
import difflib
import hashlib
import html as html_module
import importlib
import json
import platform
import re
import shutil
import socket
import statistics
import string
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import yaml

__version__ = "0.3.14"

EXIT_PASS = 0
EXIT_FAIL = 10
EXIT_BAD_SPEC = 2
EXIT_HASH_MISMATCH = 3

SCRIPT_DIR = Path(__file__).resolve().parent
TEMPLATE_PATH = SCRIPT_DIR / "examples" / "template.yaml"
SCHEMA_PATH = SCRIPT_DIR / "hypothesis.schema.yaml"
FALSIFY_DIR = Path(".falsify")

# Inlined data files (v0.2.0): pyproject.toml's py-modules layout cannot ship
# data files in the wheel under setuptools, so the file paths above only resolve
# in dev mode. The constants below are the source of truth bundled inside the
# Python module itself, ensuring `falsify init` and `falsify lock` work on a
# clean `pip install falsify` without any external file fetch.
_BUNDLED_SCHEMA_YAML = """\
schema_version: 1

type: object
required:
  - claim
  - falsification
  - experiment

properties:

  claim:
    type: string
    required: true
    description: >
      One-sentence hypothesis that can, in principle, be proven wrong.
      Must be a concrete, falsifiable statement — not a vibe.

  falsification:
    type: object
    required: true
    description: >
      The conditions under which the claim is considered falsified.
    properties:
      failure_criteria:
        type: array
        required: true
        min_items: 1
        description: >
          One or more conditions. If ANY criterion triggers on a run,
          the claim is FAIL.
        items:
          type: object
          required: [metric, direction, threshold]
          properties:
            metric:
              type: string
              description: >
                Name of the metric. Must be a key returned by the
                experiment's metric_fn.
            direction:
              type: string
              enum: [above, below, equals]
              description: >
                Direction that must hold for the claim to PASS.
                Comparisons are STRICT — boundary equality FAILS.
                  above:  observed >  threshold  (strictly greater, NOT >=)
                  below:  observed <  threshold  (strictly less,    NOT <=)
                  equals: |observed - threshold| < 1e-9
                A claim like "at least N" with integer values must set
                threshold to N-1 and direction to above (so observed=N
                PASSes as N > N-1). Setting threshold=N with direction
                above would FAIL at the exact boundary.
            threshold:
              type: number
              description: Numeric threshold the metric is compared to.
      minimum_sample_size:
        type: integer
        required: true
        minimum: 1
        description: >
          Minimum n before a verdict is considered valid. Runs with
          fewer samples return an indeterminate verdict, not PASS.
      stopping_rule:
        type: string
        required: true
        description: >
          When to stop collecting evidence — e.g. "after 1000 samples"
          or "after 1 epoch over the eval set". Locked at pre-registration
          time to prevent optional stopping.

  experiment:
    type: object
    required: true
    description: The reproducible procedure that generates evidence.
    properties:
      command:
        type: string
        required: true
        description: Shell command that runs the experiment.
      dataset:
        type: string
        required: false
        description: Path or identifier of the dataset under test.
      metric_fn:
        type: string
        required: true
        pattern: "^[A-Za-z_][\\\\w.]*:[A-Za-z_]\\\\w*$"
        description: >
          Dotted import path and function, separated by a colon.
          Example: "my_pkg.metrics:accuracy". The function must return
          a dict keyed by metric name.

  environment:
    type: object
    required: false
    description: Environment pins used to reproduce the run.
    properties:
      python:
        type: string
        description: Python version spec, e.g. "3.11" or ">=3.11,<3.13".
      packages:
        type: array
        items:
          type: string
          description: PEP-508 requirement string, e.g. "numpy==2.0.0".

  artifacts:
    type: object
    required: false
    description: Files the experiment is expected to produce.
    properties:
      outputs:
        type: array
        items:
          type: string
          description: Path (glob allowed) of an expected output artifact.

placeholder_markers:
  - "<"
  - "TODO"
  - "FIXME"
  - "REPLACE_ME"
  - "XXX"
"""

_BUNDLED_TEMPLATE_YAML = """\
# Falsification Engine — claim spec
#
# Fill in every placeholder before running `falsify lock`.
# Placeholders: "<...>", TODO, FIXME, REPLACE_ME, XXX.
# A spec with any placeholder left in a string field cannot be locked
# (the CLI will exit 2: bad spec).

claim: "<one-sentence hypothesis that can, in principle, be proven wrong>"

falsification:
  failure_criteria:
    - metric: "<metric name, must match a key returned by metric_fn>"
      direction: "<above|below|equals>"
      threshold: 0.0  # TODO: real threshold
  minimum_sample_size: 1  # TODO: real n
  stopping_rule: "<when to stop — e.g. 'after 1000 samples' or 'after 1 epoch'>"

experiment:
  command: "<shell command that runs the experiment, e.g. python run.py>"
  dataset: "<path or identifier of the dataset under test>"
  metric_fn: "<module:function>"  # e.g. my_pkg.metrics:accuracy

environment:
  python: "3.11"
  packages:
    - "<package==version>"

artifacts:
  outputs:
    - "<path/to/expected/output>"
"""

_FALLBACK_PLACEHOLDER_MARKERS = ("<", "TODO", "FIXME", "REPLACE_ME", "XXX")
_RUN_TIMEOUT_S = 300
_EQUALS_EPSILON = 1e-9

_AFFIRMATIVE_KEYWORDS = (
    "confirmed",
    "proven",
    "validated",
    "works",
    "successful",
)

EXIT_GUARD_VIOLATION = 11

_TYPE_CHECKERS: dict[str, Callable[[Any], bool]] = {
    "string": lambda v: isinstance(v, str),
    "integer": lambda v: isinstance(v, int) and not isinstance(v, bool),
    "number": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
    "array": lambda v: isinstance(v, list),
    "object": lambda v: isinstance(v, dict),
    "boolean": lambda v: isinstance(v, bool),
}


_INIT_TEMPLATES: dict[str, dict[str, str]] = {
    "accuracy": {
        "spec.yaml": (
            'claim: "Classifier accuracy is at least 80% on the holdout sample."\n'
            "falsification:\n"
            "  failure_criteria:\n"
            "    - metric: accuracy\n"
            "      direction: above\n"
            "      threshold: 0.80\n"
            "  minimum_sample_size: 20\n"
            '  stopping_rule: "fixed-n"\n'
            "experiment:\n"
            '  command: "echo ready"\n'
            '  dataset: "data.csv"\n'
            '  metric_fn: "__MODULE_PATH__.metric:accuracy"\n'
        ),
        "metric.py": (
            '"""Classifier accuracy: matches / total."""\n'
            "import csv\n"
            "from pathlib import Path\n\n"
            "def accuracy(_run_dir):\n"
            '    path = Path(__file__).parent / "data.csv"\n'
            "    rows = list(csv.DictReader(path.open()))\n"
            "    if not rows:\n"
            "        return 0.0, 0\n"
            '    correct = sum(1 for r in rows if r["predicted"] == r["actual"])\n'
            "    return correct / len(rows), len(rows)\n"
        ),
        "data.csv": (
            "id,predicted,actual\n"
            "1,cat,cat\n2,dog,dog\n3,bird,bird\n4,cat,dog\n5,dog,dog\n"
            "6,cat,cat\n7,bird,bird\n8,dog,bird\n9,cat,cat\n10,dog,dog\n"
            "11,bird,bird\n12,cat,cat\n13,dog,bird\n14,cat,cat\n15,dog,dog\n"
            "16,bird,bird\n17,cat,cat\n18,dog,dog\n19,bird,bird\n20,cat,cat\n"
        ),
        "README.md": (
            "# accuracy template\n\n"
            "Asserts a classifier's holdout accuracy is at least 80%.\n\n"
            "**Files:** `spec.yaml` (claim + threshold), `metric.py`\n"
            "(stdlib `csv` reader), `data.csv` (20 hand-crafted rows,\n"
            "17 correct → 0.85). The shipped data passes; mutate it to\n"
            "make it fail.\n\n"
            "**Modify:** swap `data.csv` for your own holdout, retune\n"
            "the `threshold` in `spec.yaml`, then `lock --force`.\n"
            "See [TUTORIAL.md](../../TUTORIAL.md) for the full pipeline.\n"
        ),
    },
    "latency": {
        "spec.yaml": (
            'claim: "P95 request latency stays below 200ms."\n'
            "falsification:\n"
            "  failure_criteria:\n"
            "    - metric: p95_latency_ms\n"
            "      direction: below\n"
            "      threshold: 200\n"
            "  minimum_sample_size: 20\n"
            '  stopping_rule: "fixed-n"\n'
            "experiment:\n"
            '  command: "echo ready"\n'
            '  dataset: "data.csv"\n'
            '  metric_fn: "__MODULE_PATH__.metric:p95_latency"\n'
        ),
        "metric.py": (
            '"""P95 latency: nearest-rank percentile over latency_ms column."""\n'
            "import csv\n"
            "import math\n"
            "from pathlib import Path\n\n"
            "def p95_latency(_run_dir):\n"
            '    path = Path(__file__).parent / "data.csv"\n'
            '    values = sorted(float(r["latency_ms"])\n'
            "                    for r in csv.DictReader(path.open()))\n"
            "    n = len(values)\n"
            "    if n == 0:\n"
            "        return 0.0, 0\n"
            "    idx = max(0, math.ceil(0.95 * n) - 1)\n"
            "    return values[idx], n\n"
        ),
        "data.csv": (
            "request_id,latency_ms\n"
            "r01,52\nr02,67\nr03,71\nr04,84\nr05,55\n"
            "r06,90\nr07,73\nr08,68\nr09,82\nr10,95\n"
            "r11,77\nr12,61\nr13,88\nr14,79\nr15,66\n"
            "r16,103\nr17,124\nr18,182\nr19,191\nr20,196\n"
        ),
        "README.md": (
            "# latency template\n\n"
            "Asserts a service's p95 request latency stays under 200ms.\n\n"
            "**Files:** `spec.yaml` (threshold = 200, direction = below),\n"
            "`metric.py` (nearest-rank p95 over the `latency_ms` column),\n"
            "`data.csv` (20 hand-crafted samples; sorted index 18 is 191ms).\n\n"
            "**Modify:** point `data.csv` at your own benchmark output,\n"
            "tune `threshold` in `spec.yaml`, then `lock --force`. See\n"
            "[TUTORIAL.md](../../TUTORIAL.md).\n"
        ),
    },
    "brier": {
        "spec.yaml": (
            'claim: "Probabilistic predictions are calibrated (Brier score below 0.25)."\n'
            "falsification:\n"
            "  failure_criteria:\n"
            "    - metric: brier_score\n"
            "      direction: below\n"
            "      threshold: 0.25\n"
            "  minimum_sample_size: 20\n"
            '  stopping_rule: "fixed-n"\n'
            "experiment:\n"
            '  command: "echo ready"\n'
            '  dataset: "data.csv"\n'
            '  metric_fn: "__MODULE_PATH__.metric:brier_score"\n'
        ),
        "metric.py": (
            '"""Brier score: mean squared error between predicted_prob and actual."""\n'
            "import csv\n"
            "from pathlib import Path\n\n"
            "def brier_score(_run_dir):\n"
            '    path = Path(__file__).parent / "data.csv"\n'
            "    rows = list(csv.DictReader(path.open()))\n"
            "    if not rows:\n"
            "        return 0.0, 0\n"
            '    total = sum((float(r["predicted_prob"]) - float(r["actual"])) ** 2\n'
            "                for r in rows)\n"
            "    return total / len(rows), len(rows)\n"
        ),
        "data.csv": (
            "event_id,predicted_prob,actual\n"
            "e01,0.90,1\ne02,0.10,0\ne03,0.85,1\ne04,0.15,0\ne05,0.92,1\n"
            "e06,0.08,0\ne07,0.78,1\ne08,0.22,0\ne09,0.88,1\ne10,0.12,0\n"
            "e11,0.83,1\ne12,0.18,0\ne13,0.95,1\ne14,0.05,0\ne15,0.80,1\n"
            "e16,0.20,0\ne17,0.85,0\ne18,0.15,1\ne19,0.90,1\ne20,0.10,0\n"
        ),
        "README.md": (
            "# brier template\n\n"
            "Asserts probabilistic predictions are calibrated: Brier\n"
            "score (mean squared error vs the binary actual) below 0.25.\n\n"
            "**Files:** `spec.yaml`, `metric.py` (one-liner Brier), and\n"
            "20 rows of `(event_id, predicted_prob, actual)` in\n"
            "`data.csv`. Shipped data has 18 confident-correct + 2\n"
            "confident-wrong → Brier ≈ 0.09.\n\n"
            "**Modify:** swap in your model's calibration data; retune\n"
            "threshold; `lock --force`. See [TUTORIAL.md](../../TUTORIAL.md).\n"
        ),
    },
    "llm-judge": {
        "spec.yaml": (
            'claim: "LLM judges agree with the reference at least 75% of the time."\n'
            "falsification:\n"
            "  failure_criteria:\n"
            "    - metric: agreement_rate\n"
            "      direction: above\n"
            "      threshold: 0.75\n"
            "  minimum_sample_size: 20\n"
            '  stopping_rule: "fixed-n"\n'
            "experiment:\n"
            '  command: "echo ready"\n'
            '  dataset: "data.jsonl"\n'
            '  metric_fn: "__MODULE_PATH__.metric:agreement_rate"\n'
        ),
        "metric.py": (
            '"""LLM-judge agreement rate: fraction of rows where agreement is true."""\n'
            "import json\n"
            "from pathlib import Path\n\n"
            "def agreement_rate(_run_dir):\n"
            '    path = Path(__file__).parent / "data.jsonl"\n'
            "    rows = []\n"
            "    with path.open() as f:\n"
            "        for line in f:\n"
            "            line = line.strip()\n"
            "            if line:\n"
            "                rows.append(json.loads(line))\n"
            "    if not rows:\n"
            "        return 0.0, 0\n"
            '    agree = sum(1 for r in rows if r.get("agreement"))\n'
            "    return agree / len(rows), len(rows)\n"
        ),
        "data.jsonl": (
            '{"prompt": "2+2?", "answer_a": "4", "answer_b": "Four", "agreement": true}\n'
            '{"prompt": "Capital of France?", "answer_a": "Paris", "answer_b": "Paris", "agreement": true}\n'
            '{"prompt": "Color of the sky?", "answer_a": "Blue", "answer_b": "Cyan", "agreement": false}\n'
            '{"prompt": "Speed of light unit?", "answer_a": "m/s", "answer_b": "meters per second", "agreement": true}\n'
            '{"prompt": "Largest ocean?", "answer_a": "Pacific", "answer_b": "Pacific Ocean", "agreement": true}\n'
            '{"prompt": "Pi to 2 decimals?", "answer_a": "3.14", "answer_b": "3.14159", "agreement": false}\n'
            '{"prompt": "Author of 1984?", "answer_a": "Orwell", "answer_b": "George Orwell", "agreement": true}\n'
            '{"prompt": "Boiling point of water (C)?", "answer_a": "100", "answer_b": "100", "agreement": true}\n'
            '{"prompt": "Number of planets?", "answer_a": "8", "answer_b": "9", "agreement": false}\n'
            '{"prompt": "JS framework by Facebook?", "answer_a": "React", "answer_b": "React.js", "agreement": true}\n'
            '{"prompt": "DNA base count?", "answer_a": "4", "answer_b": "Four", "agreement": true}\n'
            '{"prompt": "Symbol for gold?", "answer_a": "Au", "answer_b": "Au", "agreement": true}\n'
            '{"prompt": "Sum of angles in triangle?", "answer_a": "180", "answer_b": "180 degrees", "agreement": true}\n'
            '{"prompt": "Tallest mountain?", "answer_a": "Everest", "answer_b": "K2", "agreement": false}\n'
            '{"prompt": "Currency of Japan?", "answer_a": "Yen", "answer_b": "Japanese Yen", "agreement": true}\n'
            '{"prompt": "First president of USA?", "answer_a": "Washington", "answer_b": "George Washington", "agreement": true}\n'
            '{"prompt": "HTTP status for OK?", "answer_a": "200", "answer_b": "200", "agreement": true}\n'
            '{"prompt": "Atomic number of H?", "answer_a": "1", "answer_b": "1", "agreement": true}\n'
            '{"prompt": "Author of Hamlet?", "answer_a": "Shakespeare", "answer_b": "William Shakespeare", "agreement": true}\n'
            '{"prompt": "Sides of a hexagon?", "answer_a": "6", "answer_b": "6", "agreement": true}\n'
        ),
        "README.md": (
            "# llm-judge template\n\n"
            "Asserts your LLM-judge agrees with the reference at least\n"
            "75% of the time across pairwise prompts.\n\n"
            "**Files:** `spec.yaml`, `metric.py` (counts the\n"
            "`agreement` field), `data.jsonl` (20 prompts; 16 marked\n"
            "agreement=true → 0.80).\n\n"
            "**To plug in a real LLM judge:** rewrite `metric.py` to\n"
            "send each `(prompt, answer_a, answer_b)` triple to your\n"
            "judge model and recompute `agreement` at evaluation time.\n"
            "Then `lock --force`. See [TUTORIAL.md](../../TUTORIAL.md).\n"
        ),
    },
    "ab": {
        "spec.yaml": (
            'claim: "Variant B has at least a 5 percentage-point absolute lift over A."\n'
            "falsification:\n"
            "  failure_criteria:\n"
            "    - metric: ab_lift\n"
            "      direction: above\n"
            "      threshold: 0.05\n"
            "  minimum_sample_size: 20\n"
            '  stopping_rule: "fixed-n"\n'
            "experiment:\n"
            '  command: "echo ready"\n'
            '  dataset: "data.csv"\n'
            '  metric_fn: "__MODULE_PATH__.metric:ab_lift"\n'
        ),
        "metric.py": (
            '"""A/B test lift: conversion(B) - conversion(A)."""\n'
            "import csv\n"
            "from pathlib import Path\n\n"
            "def ab_lift(_run_dir):\n"
            '    path = Path(__file__).parent / "data.csv"\n'
            "    rows = list(csv.DictReader(path.open()))\n"
            "    if not rows:\n"
            "        return 0.0, 0\n"
            '    a = [r for r in rows if r["variant"] == "a"]\n'
            '    b = [r for r in rows if r["variant"] == "b"]\n'
            "    if not a or not b:\n"
            "        return 0.0, len(rows)\n"
            '    rate_a = sum(int(r["converted"]) for r in a) / len(a)\n'
            '    rate_b = sum(int(r["converted"]) for r in b) / len(b)\n'
            "    return rate_b - rate_a, len(rows)\n"
        ),
        "data.csv": (
            "user_id,variant,converted\n"
            "u01,a,0\nu02,a,1\nu03,a,0\nu04,a,1\nu05,a,0\n"
            "u06,a,0\nu07,a,0\nu08,a,0\nu09,a,0\nu10,a,0\n"
            "u11,b,0\nu12,b,1\nu13,b,1\nu14,b,0\nu15,b,1\n"
            "u16,b,0\nu17,b,0\nu18,b,0\nu19,b,0\nu20,b,0\n"
        ),
        "README.md": (
            "# ab template\n\n"
            "Asserts that variant B's conversion rate exceeds variant\n"
            "A's by at least 5 percentage points (absolute lift).\n\n"
            "**Files:** `spec.yaml` (threshold 0.05, direction above),\n"
            "`metric.py` (lift = rate_b - rate_a), `data.csv` (20 rows,\n"
            "10 per variant; A=0.20, B=0.30 → lift 0.10).\n\n"
            "**Modify:** swap in your real experiment's per-user\n"
            "conversions; the column names (`variant`, `converted`)\n"
            "are what the metric reads. `lock --force` after edits.\n"
            "See [TUTORIAL.md](../../TUTORIAL.md).\n"
        ),
    },
}


def _cmd_init_template(args: argparse.Namespace) -> int:
    template_name = args.template
    if template_name not in _INIT_TEMPLATES:
        avail = ", ".join(sorted(_INIT_TEMPLATES))
        print(
            f"falsify init: unknown template {template_name!r}; "
            f"available: {avail}",
            file=sys.stderr,
        )
        return EXIT_BAD_SPEC

    # Default to a Python-import-safe name (snake_case) when the
    # template flag uses kebab-case (e.g. --template llm-judge).
    default_name = template_name.replace("-", "_")
    name = args.claim_name or args.name or default_name
    target_dir = Path(args.dir) if args.dir else Path("claims") / name
    files = _INIT_TEMPLATES[template_name]

    if target_dir.exists():
        existing = [
            f for f in files
            if (target_dir / f).exists()
        ]
        if existing and not args.force:
            print(
                f"falsify init: files exist; use --force to overwrite: "
                f"{', '.join(existing)} in {target_dir}",
                file=sys.stderr,
            )
            return EXIT_BAD_SPEC

    module_path = (
        str(target_dir).replace("\\", "/").replace("/", ".").strip(".")
    )

    target_dir.mkdir(parents=True, exist_ok=True)
    for filename, content in files.items():
        rendered = (
            content
            .replace("__MODULE_PATH__", module_path)
            .replace("__NAME__", name)
        )
        (target_dir / filename).write_text(rendered)

    falsify_dir = FALSIFY_DIR / name
    falsify_dir.mkdir(parents=True, exist_ok=True)
    (falsify_dir / "spec.yaml").write_text(
        (target_dir / "spec.yaml").read_text()
    )

    print(f"Scaffolded `{template_name}` template at {target_dir}/")
    print(f"  spec mirrored to .falsify/{name}/spec.yaml")
    print()
    print("Next steps:")
    print(f"  python3 falsify.py lock {name}")
    print(f"  python3 falsify.py run {name}")
    print(f"  python3 falsify.py verdict {name}")
    return EXIT_PASS


def cmd_init(args: argparse.Namespace) -> int:
    if args.template:
        return _cmd_init_template(args)

    name = args.name or args.claim_name
    if not name:
        print(
            "falsify init: claim name required (positional or --name) "
            "unless --template is given",
            file=sys.stderr,
        )
        return 1

    target_dir = FALSIFY_DIR / name
    spec_path = target_dir / "spec.yaml"

    if target_dir.exists() and not args.force:
        print(
            f"falsify init: {target_dir} already exists "
            f"(use --force to overwrite)",
            file=sys.stderr,
        )
        return 1

    target_dir.mkdir(parents=True, exist_ok=True)
    if TEMPLATE_PATH.exists():
        spec_path.write_text(TEMPLATE_PATH.read_text())
    else:
        # Fallback: bundled template (pip-installed wheel ships data inline).
        spec_path.write_text(_BUNDLED_TEMPLATE_YAML)

    print(f"Created {spec_path}")
    print("Next: edit the spec, replace placeholders, then `falsify lock`.")
    return EXIT_PASS


def _load_schema() -> dict:
    if SCHEMA_PATH.exists():
        with SCHEMA_PATH.open() as f:
            return yaml.safe_load(f)
    # Fallback: bundled schema (used when installed via pip wheel where the
    # external file isn't shipped). See _BUNDLED_SCHEMA_YAML at the top of
    # this module.
    return yaml.safe_load(_BUNDLED_SCHEMA_YAML)


def _collect_required_keys(node: dict) -> list[str]:
    top = node.get("required")
    if isinstance(top, list):
        return list(top)
    props = node.get("properties") or {}
    return [
        k for k, v in props.items()
        if isinstance(v, dict) and v.get("required") is True
    ]


def _validate_against_schema(
    value: Any,
    schema: dict,
    path: str,
    errors: list[str],
) -> None:
    ty = schema.get("type")
    if ty in _TYPE_CHECKERS and not _TYPE_CHECKERS[ty](value):
        errors.append(
            f"{path or '<root>'}: expected {ty}, got {type(value).__name__}"
        )
        return

    enum = schema.get("enum")
    if enum is not None and value not in enum:
        errors.append(f"{path}: {value!r} not in {list(enum)}")

    pattern = schema.get("pattern")
    if pattern and isinstance(value, str) and not re.match(pattern, value):
        errors.append(f"{path}: {value!r} does not match pattern {pattern!r}")

    minimum = schema.get("minimum")
    if (
        minimum is not None
        and isinstance(value, (int, float))
        and not isinstance(value, bool)
        and value < minimum
    ):
        errors.append(f"{path}: must be >= {minimum} (got {value})")

    if ty == "object" and isinstance(value, dict):
        for key in _collect_required_keys(schema):
            if key not in value:
                prefix = f"{path}." if path else ""
                errors.append(f"{prefix}{key}: missing required field")
        props = schema.get("properties") or {}
        for key, sub in value.items():
            if key in props and isinstance(props[key], dict):
                sub_path = f"{path}.{key}" if path else key
                _validate_against_schema(sub, props[key], sub_path, errors)

    if ty == "array" and isinstance(value, list):
        min_items = schema.get("min_items")
        if isinstance(min_items, int) and len(value) < min_items:
            errors.append(
                f"{path}: must have at least {min_items} item(s) (got {len(value)})"
            )
        items_schema = schema.get("items")
        if isinstance(items_schema, dict):
            for i, item in enumerate(value):
                _validate_against_schema(
                    item, items_schema, f"{path}[{i}]", errors
                )


def _find_placeholders(
    value: Any,
    markers: tuple[str, ...],
    path: str = "",
) -> list[tuple[str, str]]:
    found: list[tuple[str, str]] = []
    if isinstance(value, dict):
        for k, v in value.items():
            sub = f"{path}.{k}" if path else k
            found.extend(_find_placeholders(v, markers, sub))
    elif isinstance(value, list):
        for i, item in enumerate(value):
            found.extend(_find_placeholders(item, markers, f"{path}[{i}]"))
    elif isinstance(value, str):
        for marker in markers:
            if marker in value:
                found.append((path, value))
                break
    return found


def _canonicalize(spec: Any) -> str:
    """Render a YAML tree in a stable form suitable for hashing."""
    return yaml.safe_dump(
        spec,
        sort_keys=True,
        default_flow_style=False,
        allow_unicode=True,
        width=4096,
    )


def cmd_lock(args: argparse.Namespace) -> int:
    claim_dir = FALSIFY_DIR / args.name
    spec_path = claim_dir / "spec.yaml"
    lock_path = claim_dir / "spec.lock.json"

    if not spec_path.exists():
        print(
            f"falsify lock: {spec_path} not found — "
            f"run `falsify init {args.name}` first",
            file=sys.stderr,
        )
        return 1

    try:
        raw_text = spec_path.read_text()
        spec = yaml.safe_load(raw_text)
    except yaml.YAMLError as e:
        print(f"falsify lock: failed to parse {spec_path}: {e}", file=sys.stderr)
        return EXIT_BAD_SPEC

    if not isinstance(spec, dict):
        print(
            f"falsify lock: {spec_path} must be a YAML mapping at the top level",
            file=sys.stderr,
        )
        return EXIT_BAD_SPEC

    schema = _load_schema()

    markers_raw = schema.get("placeholder_markers") or _FALLBACK_PLACEHOLDER_MARKERS
    markers = tuple(str(m) for m in markers_raw)
    placeholders = _find_placeholders(spec, markers)
    if placeholders:
        print(
            f"falsify lock: {spec_path} still contains placeholder values:",
            file=sys.stderr,
        )
        for field_path, val in placeholders:
            print(f"  - {field_path}: {val!r}", file=sys.stderr)
        print(
            "Replace placeholders with real values, then re-run `falsify lock`.",
            file=sys.stderr,
        )
        return EXIT_BAD_SPEC

    errors: list[str] = []
    _validate_against_schema(spec, schema, "", errors)
    if errors:
        print(f"falsify lock: invalid spec {spec_path}:", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        return EXIT_BAD_SPEC

    canonical = _canonicalize(spec)
    spec_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    if lock_path.exists() and not args.force:
        try:
            existing = json.loads(lock_path.read_text())
        except json.JSONDecodeError:
            existing = None
        if isinstance(existing, dict):
            existing_hash = existing.get("spec_hash")
            if isinstance(existing_hash, str):
                if existing_hash == spec_hash:
                    print(
                        f"Already locked {args.name} @ {spec_hash[:12]} "
                        f"— spec unchanged."
                    )
                    return EXIT_PASS
                print(
                    f"falsify lock: {spec_path} has been modified since last lock "
                    f"(was {existing_hash[:12]}, now {spec_hash[:12]}). "
                    f"Use --force to relock.",
                    file=sys.stderr,
                )
                return EXIT_HASH_MISMATCH

    lock_data = {
        "spec_hash": spec_hash,
        "locked_at": datetime.now(timezone.utc).isoformat(),
        "canonical_yaml": canonical,
    }
    lock_path.write_text(
        json.dumps(lock_data, indent=2, sort_keys=True) + "\n"
    )

    print(f"✓ Locked {args.name} @ {spec_hash[:12]}")
    for c in spec["falsification"]["failure_criteria"]:
        print(f"  claim: {c['metric']} {c['direction']} {c['threshold']}")
    return EXIT_PASS


def _render_unified_diff(
    a_text: str, b_text: str, label_a: str, label_b: str
) -> None:
    """Write a colored unified diff to stdout.

    ANSI escapes are emitted only when stdout is a TTY.
    """
    use_color = sys.stdout.isatty()
    for line in difflib.unified_diff(
        a_text.splitlines(keepends=True),
        b_text.splitlines(keepends=True),
        fromfile=label_a,
        tofile=label_b,
    ):
        if use_color:
            if line.startswith("+++") or line.startswith("---"):
                line = "\x1b[1m" + line + "\x1b[0m"
            elif line.startswith("+"):
                line = "\x1b[32m" + line + "\x1b[0m"
            elif line.startswith("-"):
                line = "\x1b[31m" + line + "\x1b[0m"
            elif line.startswith("@@"):
                line = "\x1b[36m" + line + "\x1b[0m"
        sys.stdout.write(line)


def _canonical_and_hash(spec: Any) -> tuple[str, str]:
    canonical = _canonicalize(spec)
    return canonical, hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _diff_file_vs_file(path_a: Path, path_b: Path) -> int:
    for p in (path_a, path_b):
        if not p.exists():
            print(f"falsify diff: {p} not found", file=sys.stderr)
            return EXIT_BAD_SPEC
    try:
        spec_a = yaml.safe_load(path_a.read_text())
        spec_b = yaml.safe_load(path_b.read_text())
    except yaml.YAMLError as e:
        print(f"falsify diff: YAML parse error: {e}", file=sys.stderr)
        return EXIT_BAD_SPEC

    yaml_a, hash_a = _canonical_and_hash(spec_a)
    yaml_b, hash_b = _canonical_and_hash(spec_b)

    if yaml_a == yaml_b:
        print(f"Files are canonically identical @ {hash_a[:12]}")
        return EXIT_PASS

    _render_unified_diff(
        yaml_a, yaml_b,
        f"{path_a}@{hash_a[:12]}",
        f"{path_b}@{hash_b[:12]}",
    )
    return EXIT_HASH_MISMATCH


def _diff_lock_vs_file(name: str) -> int:
    claim_dir = FALSIFY_DIR / name
    spec_path = claim_dir / "spec.yaml"
    lock_path = claim_dir / "spec.lock.json"

    if not spec_path.exists():
        print(
            f"falsify diff: {spec_path} not found — "
            f"run `falsify init {name}` first",
            file=sys.stderr,
        )
        return EXIT_BAD_SPEC
    if not lock_path.exists():
        print(
            f"falsify diff: no lock at {lock_path} — "
            f"run `falsify lock {name}` first",
            file=sys.stderr,
        )
        return EXIT_BAD_SPEC

    try:
        lock_data = json.loads(lock_path.read_text())
    except (OSError, json.JSONDecodeError) as e:
        print(f"falsify diff: failed to read {lock_path}: {e}", file=sys.stderr)
        return EXIT_BAD_SPEC

    locked_hash = lock_data.get("spec_hash") if isinstance(lock_data, dict) else None
    locked_yaml = (
        lock_data.get("canonical_yaml") if isinstance(lock_data, dict) else None
    )

    try:
        current_spec = yaml.safe_load(spec_path.read_text())
    except yaml.YAMLError as e:
        print(f"falsify diff: failed to parse {spec_path}: {e}", file=sys.stderr)
        return EXIT_BAD_SPEC

    current_yaml, current_hash = _canonical_and_hash(current_spec)

    if not isinstance(locked_yaml, str):
        if isinstance(locked_hash, str) and locked_hash == current_hash:
            print(
                f"Lock has no canonical_yaml field (legacy format). "
                f"Spec is unchanged @ {current_hash[:12]}; nothing to diff."
            )
            print(
                f"Re-lock with `falsify lock {name} --force` to populate "
                f"canonical_yaml for future diffs.",
            )
            return EXIT_PASS
        print(
            f"falsify diff: legacy lock — no canonical_yaml stored and "
            f"spec has drifted. Re-lock with "
            f"`falsify lock {name} --force` to enable diff.",
            file=sys.stderr,
        )
        return EXIT_BAD_SPEC

    locked_short = (locked_hash or "?")[:12]
    current_short = current_hash[:12]

    if locked_yaml == current_yaml:
        print(f"Lock and current spec are identical @ {current_short}")
        return EXIT_PASS

    _render_unified_diff(
        locked_yaml,
        current_yaml,
        f"locked@{locked_short}",
        f"current@{current_short}",
    )
    return EXIT_HASH_MISMATCH


def cmd_diff(args: argparse.Namespace) -> int:
    if args.file_vs_file:
        path_a, path_b = args.file_vs_file
        return _diff_file_vs_file(Path(path_a), Path(path_b))
    if not args.name:
        print(
            "falsify diff: name is required for lock-vs-file mode "
            "(or pass --file-vs-file A B)",
            file=sys.stderr,
        )
        return EXIT_BAD_SPEC
    return _diff_lock_vs_file(args.name)


def _load_locked_spec(
    claim_dir: Path,
) -> tuple[dict | None, dict | None, str]:
    """Return (spec, lock_data, error_message). On error, spec and lock are None."""
    spec_path = claim_dir / "spec.yaml"
    lock_path = claim_dir / "spec.lock.json"

    if not lock_path.exists():
        return None, None, (
            f"no locked spec at {lock_path} — "
            f"run `falsify lock {claim_dir.name}` first."
        )
    if not spec_path.exists():
        return None, None, f"{spec_path} not found."

    try:
        spec = yaml.safe_load(spec_path.read_text())
    except yaml.YAMLError as e:
        return None, None, f"failed to parse {spec_path}: {e}"
    try:
        lock_data = json.loads(lock_path.read_text())
    except json.JSONDecodeError as e:
        return None, None, f"failed to parse {lock_path}: {e}"

    return spec, lock_data, ""


def _verify_lock_hash(spec: dict, lock_data: dict) -> bool:
    current_hash = hashlib.sha256(
        _canonicalize(spec).encode("utf-8")
    ).hexdigest()
    return lock_data.get("spec_hash") == current_hash


def _update_latest_pointer(claim_dir: Path, timestamp: str) -> None:
    latest = claim_dir / "latest_run"
    if latest.is_symlink() or latest.exists():
        latest.unlink()
    try:
        latest.symlink_to(Path("runs") / timestamp)
    except OSError:
        latest.write_text(timestamp + "\n")


def _resolve_latest_run(claim_dir: Path) -> Path | None:
    latest = claim_dir / "latest_run"
    if latest.is_symlink():
        target = latest.readlink()
        if target.is_absolute():
            return target
        return (claim_dir / target).resolve()
    if latest.is_file():
        ts = latest.read_text().strip()
        if ts:
            return claim_dir / "runs" / ts
    return None


def cmd_run(args: argparse.Namespace) -> int:
    claim_dir = FALSIFY_DIR / args.name
    spec, lock_data, err = _load_locked_spec(claim_dir)
    if err:
        print(f"falsify run: {err}", file=sys.stderr)
        return EXIT_BAD_SPEC

    assert spec is not None and lock_data is not None
    if not _verify_lock_hash(spec, lock_data):
        print(
            f"falsify run: spec modified after lock. "
            f"Re-lock with `falsify lock {args.name} --force`.",
            file=sys.stderr,
        )
        return EXIT_HASH_MISMATCH

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ")
    run_dir = claim_dir / "runs" / timestamp
    run_dir.mkdir(parents=True, exist_ok=True)

    (run_dir / "spec.lock.json").write_text(
        (claim_dir / "spec.lock.json").read_text()
    )

    command = spec["experiment"]["command"]
    start = datetime.now(timezone.utc)
    timed_out = False
    try:
        # The command comes from the user's own spec file and runs on the
        # user's own machine — the spec author IS the executor (same trust
        # model as make / npm scripts / tox). shell=True is intentional so
        # experiment commands can use pipes, redirection and env expansion.
        result = subprocess.run(
            command,
            shell=True,  # nosec B602 — user's own spec command, no trust boundary crossed
            capture_output=True,
            text=True,
            timeout=_RUN_TIMEOUT_S,
            cwd=str(Path.cwd()),
        )
        stdout, stderr, returncode = (
            result.stdout,
            result.stderr,
            result.returncode,
        )
    except subprocess.TimeoutExpired as e:
        stdout = e.stdout or ""
        stderr = (e.stderr or "") + f"\n[timeout after {_RUN_TIMEOUT_S}s]\n"
        returncode = 124
        timed_out = True
    end = datetime.now(timezone.utc)

    (run_dir / "stdout.txt").write_text(stdout)
    (run_dir / "stderr.txt").write_text(stderr)

    meta = {
        "command": command,
        "start": start.isoformat(),
        "end": end.isoformat(),
        "duration_s": round((end - start).total_seconds(), 6),
        "returncode": returncode,
        "timed_out": timed_out,
        "hostname": socket.gethostname(),
        "python_version": platform.python_version(),
    }
    (run_dir / "run_meta.json").write_text(
        json.dumps(meta, indent=2, sort_keys=True) + "\n"
    )

    _update_latest_pointer(claim_dir, timestamp)

    if returncode != 0:
        print(
            f"falsify run: command exited with code {returncode} "
            f"(run dir: {run_dir})",
            file=sys.stderr,
        )
        if stderr.strip():
            sys.stderr.write(stderr)
            if not stderr.endswith("\n"):
                sys.stderr.write("\n")
        return 1

    print(f"✓ Run {timestamp} ({meta['duration_s']:.2f}s)")
    return EXIT_PASS


def _load_metric_fn(metric_fn_spec: str) -> Callable[..., Any]:
    """Import and return the metric callable referenced by 'module:function'.

    Inserts `cwd` into sys.path so user metric modules adjacent to the
    working directory are importable. Raises ValueError if the spec
    string is malformed; propagates ImportError / AttributeError.
    """
    if ":" not in metric_fn_spec:
        raise ValueError(
            f"metric_fn {metric_fn_spec!r} must be in 'module:function' form"
        )
    module_name, func_name = metric_fn_spec.split(":", 1)
    cwd_str = str(Path.cwd())
    if cwd_str not in sys.path:
        sys.path.insert(0, cwd_str)
    module = importlib.import_module(module_name)
    return getattr(module, func_name)


def _criterion_holds(value: float, direction: str, threshold: float) -> bool:
    if direction == "above":
        return value > threshold
    if direction == "below":
        return value < threshold
    if direction == "equals":
        return abs(value - threshold) < _EQUALS_EPSILON
    raise ValueError(f"unknown direction: {direction!r}")


def cmd_replay(args: argparse.Namespace) -> int:
    run_id = args.run_id
    tolerance = args.tolerance if args.tolerance is not None else 0.0
    use_json = bool(getattr(args, "json", False))

    # Locate the run directory: optionally narrowed by --claim.
    matches: list[str] = []
    if args.claim:
        if (FALSIFY_DIR / args.claim / "runs" / run_id).is_dir():
            matches.append(args.claim)
    elif FALSIFY_DIR.exists():
        for claim_dir in sorted(FALSIFY_DIR.iterdir()):
            if not claim_dir.is_dir():
                continue
            if (claim_dir / "runs" / run_id).is_dir():
                matches.append(claim_dir.name)

    if not matches:
        msg = f"run_id {run_id!r} not found under .falsify/*/runs/"
        if use_json:
            print(json.dumps(
                {"status": "error", "run_id": run_id, "message": msg},
                indent=2, sort_keys=True,
            ))
        else:
            print(f"falsify replay: {msg}", file=sys.stderr)
        return EXIT_BAD_SPEC
    if len(matches) > 1:
        msg = (
            f"run_id {run_id!r} is ambiguous across claims "
            f"{matches}; disambiguate with --claim"
        )
        if use_json:
            print(json.dumps(
                {"status": "error", "run_id": run_id, "message": msg},
                indent=2, sort_keys=True,
            ))
        else:
            print(f"falsify replay: {msg}", file=sys.stderr)
        return EXIT_BAD_SPEC

    claim = matches[0]
    claim_dir = FALSIFY_DIR / claim
    run_dir = claim_dir / "runs" / run_id

    run_verdict_path = run_dir / "verdict.json"
    if not run_verdict_path.exists():
        msg = (
            f"run {run_id} has no verdict snapshot — run "
            f"`falsify verdict {claim}` against this run first"
        )
        if use_json:
            print(json.dumps(
                {"status": "error", "run_id": run_id, "claim": claim, "message": msg},
                indent=2, sort_keys=True,
            ))
        else:
            print(f"falsify replay: {msg}", file=sys.stderr)
        return EXIT_BAD_SPEC

    try:
        stored = json.loads(run_verdict_path.read_text())
        stored_lock = json.loads((run_dir / "spec.lock.json").read_text())
    except (OSError, json.JSONDecodeError) as e:
        if use_json:
            print(json.dumps(
                {"status": "error", "run_id": run_id, "claim": claim,
                 "message": f"failed to read run artifacts: {e}"},
                indent=2, sort_keys=True,
            ))
        else:
            print(
                f"falsify replay: failed to read run artifacts: {e}",
                file=sys.stderr,
            )
        return EXIT_BAD_SPEC

    stored_value = stored.get("observed_value")
    stored_n = stored.get("sample_size")
    stored_hash = stored_lock.get("spec_hash")

    # Check that the current spec still matches the hash at run time.
    spec_path = claim_dir / "spec.yaml"
    if not spec_path.exists():
        msg = f"{spec_path} not found"
        if use_json:
            print(json.dumps(
                {"status": "error", "run_id": run_id, "claim": claim, "message": msg},
                indent=2, sort_keys=True,
            ))
        else:
            print(f"falsify replay: {msg}", file=sys.stderr)
        return EXIT_BAD_SPEC
    try:
        current_spec = yaml.safe_load(spec_path.read_text())
    except yaml.YAMLError as e:
        if use_json:
            print(json.dumps(
                {"status": "error", "run_id": run_id, "claim": claim,
                 "message": f"spec parse error: {e}"},
                indent=2, sort_keys=True,
            ))
        else:
            print(f"falsify replay: spec parse error: {e}", file=sys.stderr)
        return EXIT_BAD_SPEC
    current_hash = hashlib.sha256(
        _canonicalize(current_spec).encode("utf-8")
    ).hexdigest()

    if stored_hash != current_hash:
        msg = (
            f"spec changed since run; replay invalid "
            f"(stored {str(stored_hash)[:12]}, current {current_hash[:12]})"
        )
        if use_json:
            print(json.dumps({
                "status": "stale",
                "claim": claim,
                "run_id": run_id,
                "stored_hash": stored_hash,
                "current_hash": current_hash,
                "message": msg,
            }, indent=2, sort_keys=True))
        else:
            print(f"falsify replay: {msg}", file=sys.stderr)
        return EXIT_HASH_MISMATCH

    metric_fn_spec = current_spec["experiment"]["metric_fn"]
    try:
        fn = _load_metric_fn(metric_fn_spec)
    except (ValueError, ImportError, AttributeError) as e:
        msg = f"failed to load {metric_fn_spec}: {e}"
        if use_json:
            print(json.dumps(
                {"status": "error", "run_id": run_id, "claim": claim, "message": msg},
                indent=2, sort_keys=True,
            ))
        else:
            print(f"falsify replay: {msg}", file=sys.stderr)
        return EXIT_BAD_SPEC

    try:
        result = fn(run_dir)
    except Exception as e:
        msg = f"metric_fn raised {type(e).__name__}: {e}"
        if use_json:
            print(json.dumps(
                {"status": "error", "run_id": run_id, "claim": claim, "message": msg},
                indent=2, sort_keys=True,
            ))
        else:
            print(f"falsify replay: {msg}", file=sys.stderr)
        return EXIT_BAD_SPEC

    if isinstance(result, tuple) and len(result) == 2:
        replay_raw, replay_n = result
    else:
        replay_raw = result
        replay_n = None
    if not isinstance(replay_raw, (int, float)) or isinstance(replay_raw, bool):
        msg = (
            f"metric_fn must return a number or (number, int); got "
            f"{type(replay_raw).__name__}"
        )
        if use_json:
            print(json.dumps(
                {"status": "error", "run_id": run_id, "claim": claim, "message": msg},
                indent=2, sort_keys=True,
            ))
        else:
            print(f"falsify replay: {msg}", file=sys.stderr)
        return EXIT_BAD_SPEC
    replay_value = float(replay_raw)

    if not isinstance(stored_value, (int, float)) or isinstance(stored_value, bool):
        msg = "stored observed_value is not a number — cannot compare"
        if use_json:
            print(json.dumps(
                {"status": "error", "run_id": run_id, "claim": claim, "message": msg},
                indent=2, sort_keys=True,
            ))
        else:
            print(f"falsify replay: {msg}", file=sys.stderr)
        return EXIT_BAD_SPEC

    delta = abs(replay_value - float(stored_value))
    value_match = delta <= tolerance
    n_match = (replay_n == stored_n) if stored_n is not None else True
    match = value_match and n_match

    if use_json:
        print(json.dumps({
            "status": "ok" if match else "mismatch",
            "claim": claim,
            "run_id": run_id,
            "stored": {"value": stored_value, "n": stored_n},
            "replayed": {"value": replay_value, "n": replay_n},
            "delta": delta,
            "tolerance": tolerance,
        }, indent=2, sort_keys=True))
    else:
        if match:
            print(
                f"REPLAY OK  claim={claim}  run={run_id}  "
                f"value={replay_value}  n={replay_n}"
            )
        else:
            print(
                f"REPLAY MISMATCH  stored={stored_value}  "
                f"replayed={replay_value}  delta={delta}"
            )

    return EXIT_PASS if match else EXIT_FAIL


def cmd_verdict(args: argparse.Namespace) -> int:
    claim_dir = FALSIFY_DIR / args.name
    spec_path = claim_dir / "spec.yaml"

    if not spec_path.exists():
        print(
            f"falsify verdict: {spec_path} not found — "
            f"run `falsify init {args.name}` first.",
            file=sys.stderr,
        )
        return EXIT_BAD_SPEC

    run_dir = _resolve_latest_run(claim_dir)
    if run_dir is None or not run_dir.exists():
        print(
            f"falsify verdict: no runs — "
            f"run `falsify run {args.name}` first.",
            file=sys.stderr,
        )
        return EXIT_BAD_SPEC

    try:
        spec = yaml.safe_load(spec_path.read_text())
    except yaml.YAMLError as e:
        print(f"falsify verdict: failed to parse {spec_path}: {e}", file=sys.stderr)
        return EXIT_BAD_SPEC

    metric_fn_spec = spec["experiment"]["metric_fn"]
    try:
        fn = _load_metric_fn(metric_fn_spec)
    except (ValueError, ImportError, AttributeError) as e:
        print(
            f"falsify verdict: failed to load {metric_fn_spec}: {e}",
            file=sys.stderr,
        )
        return EXIT_BAD_SPEC

    try:
        raw = fn(run_dir)
    except Exception as e:
        print(
            f"falsify verdict: metric_fn raised {type(e).__name__}: {e}",
            file=sys.stderr,
        )
        return 1

    sample_size: int | None = None
    if isinstance(raw, tuple) and len(raw) == 2:
        value_raw, sample_size = raw
    else:
        value_raw = raw
    if not isinstance(value_raw, (int, float)) or isinstance(value_raw, bool):
        print(
            f"falsify verdict: metric_fn must return a number "
            f"or (number, int). Got {type(value_raw).__name__}",
            file=sys.stderr,
        )
        return EXIT_BAD_SPEC
    value = float(value_raw)

    min_n = spec["falsification"]["minimum_sample_size"]
    criteria = spec["falsification"]["failure_criteria"]
    head = criteria[0]

    if sample_size is not None and sample_size < min_n:
        inconclusive = {
            "verdict": "INCONCLUSIVE",
            "reason": "minimum_sample_size_not_met",
            "observed_value": value,
            "sample_size": sample_size,
            "minimum_sample_size": min_n,
            "metric": head["metric"],
            "direction": head["direction"],
            "threshold": head["threshold"],
            "run_ref": run_dir.name,
            "checked_at": datetime.now(timezone.utc).isoformat(),
        }
        inconclusive_json = (
            json.dumps(inconclusive, indent=2, sort_keys=True) + "\n"
        )
        (claim_dir / "verdict.json").write_text(inconclusive_json)
        (run_dir / "verdict.json").write_text(inconclusive_json)
        print(
            f"falsify verdict: minimum_sample_size not met "
            f"({sample_size} < {min_n})",
            file=sys.stderr,
        )
        return EXIT_BAD_SPEC

    all_hold = True
    for c in criteria:
        if not _criterion_holds(value, c["direction"], c["threshold"]):
            all_hold = False

    verdict = "PASS" if all_hold else "FAIL"
    # Bind the verdict to the bar it was judged against. Without this, a verdict
    # judged after the spec drifted from the lock (e.g. threshold edited post-run)
    # is indistinguishable from an honest one in verdict.json alone. Embed the
    # live spec hash and the locked hash; if they differ, the verdict is stamped
    # DRIFTED so the artifact is self-revealing.
    _live_hash = _canonical_and_hash(spec)[1]
    _lock_path = claim_dir / "spec.lock.json"
    _locked_hash = None
    if _lock_path.exists():
        try:
            _locked_hash = json.loads(_lock_path.read_text()).get("spec_hash")
        except (OSError, ValueError):
            _locked_hash = None
    _drifted = bool(_locked_hash) and _locked_hash != _live_hash
    verdict_data = {
        "verdict": verdict,
        "observed_value": value,
        "threshold": head["threshold"],
        "direction": head["direction"],
        "metric": head["metric"],
        "run_ref": run_dir.name,
        "spec_hash": _live_hash,
        "locked_spec_hash": _locked_hash,
        "bar_integrity": "DRIFTED" if _drifted else ("LOCKED" if _locked_hash else "UNLOCKED"),
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }
    if sample_size is not None:
        verdict_data["sample_size"] = sample_size
    verdict_json = json.dumps(verdict_data, indent=2, sort_keys=True) + "\n"
    (claim_dir / "verdict.json").write_text(verdict_json)
    (run_dir / "verdict.json").write_text(verdict_json)

    print(f"Verdict: {verdict}")
    print(f"  observed {head['metric']} = {value}")
    print(f"  threshold: {head['direction']} {head['threshold']}")
    if _drifted:
        print(f"  ⚠ bar integrity: DRIFTED — the live spec ({_live_hash[:12]}) "
              f"differs from the locked bar ({_locked_hash[:12]}); this verdict "
              f"was NOT judged against the pre-registered threshold.", file=sys.stderr)
    return EXIT_PASS if all_hold else EXIT_FAIL


def _normalize_text(s: str) -> str:
    s = s.lower()
    s = s.translate(str.maketrans("", "", string.punctuation))
    return " ".join(s.split())


def _claim_text_matches(claim_norm: str, input_norm: str) -> bool:
    if not claim_norm or not input_norm:
        return False
    if claim_norm in input_norm or input_norm in claim_norm:
        return True
    claim_tokens = {w for w in claim_norm.split() if len(w) >= 5}
    input_tokens = {w for w in input_norm.split() if len(w) >= 5}
    return len(claim_tokens & input_tokens) >= 2


def _derive_claim_state(claim_dir: Path) -> tuple[str, dict | None]:
    """Return (state, verdict_data_or_None).

    States: PASS | FAIL | INCONCLUSIVE | STALE | UNRUN | UNLOCKED | UNKNOWN.
    """
    spec_path = claim_dir / "spec.yaml"
    lock_path = claim_dir / "spec.lock.json"
    verdict_path = claim_dir / "verdict.json"

    if not spec_path.exists():
        return "UNKNOWN", None
    if not lock_path.exists():
        return "UNLOCKED", None

    try:
        spec = yaml.safe_load(spec_path.read_text())
        current_hash = hashlib.sha256(
            _canonicalize(spec).encode("utf-8")
        ).hexdigest()
        lock_data = json.loads(lock_path.read_text())
    except (yaml.YAMLError, json.JSONDecodeError, OSError):
        return "UNKNOWN", None

    if lock_data.get("spec_hash") != current_hash:
        return "STALE", None

    if not verdict_path.exists():
        return "UNRUN", None

    try:
        verdict_data = json.loads(verdict_path.read_text())
    except (OSError, json.JSONDecodeError):
        return "UNKNOWN", None

    if not isinstance(verdict_data, dict):
        return "UNKNOWN", None

    v = verdict_data.get("verdict")
    if v in ("PASS", "FAIL", "INCONCLUSIVE"):
        return v, verdict_data
    return "UNKNOWN", verdict_data


def _read_claim_text(claim_dir: Path) -> str | None:
    spec_path = claim_dir / "spec.yaml"
    try:
        spec = yaml.safe_load(spec_path.read_text())
    except (yaml.YAMLError, OSError):
        return None
    if isinstance(spec, dict):
        claim = spec.get("claim")
        if isinstance(claim, str):
            return claim
    return None


def _iter_claim_dirs(base: Path):
    if not base.exists():
        return
    for claim_dir in sorted(base.iterdir()):
        if not claim_dir.is_dir():
            continue
        if not (claim_dir / "spec.yaml").exists():
            continue
        yield claim_dir


def _guard_text_mode(input_text: str) -> int:
    input_norm = _normalize_text(input_text)
    input_tokens = set(input_norm.split())
    if not any(kw in input_tokens for kw in _AFFIRMATIVE_KEYWORDS):
        return EXIT_PASS

    violations: list[tuple[str, str, str]] = []
    for claim_dir in _iter_claim_dirs(FALSIFY_DIR):
        state, _ = _derive_claim_state(claim_dir)
        if state == "PASS":
            continue
        if state not in ("FAIL", "INCONCLUSIVE"):
            continue
        claim_text = _read_claim_text(claim_dir)
        if claim_text is None:
            continue
        if _claim_text_matches(_normalize_text(claim_text), input_norm):
            reason = state
            if state == "INCONCLUSIVE":
                reason = "INCONCLUSIVE (not yet proven)"
            violations.append((claim_dir.name, reason, claim_text))

    if not violations:
        return EXIT_PASS

    print("BLOCKED: claim contradicts logged verdict(s):", file=sys.stderr)
    for name, reason, claim_text in violations:
        print(f"  - {name}: {reason} — {claim_text}", file=sys.stderr)
    return EXIT_GUARD_VIOLATION


def _guard_scan_mode() -> int:
    problems: list[tuple[str, str]] = []
    for claim_dir in _iter_claim_dirs(FALSIFY_DIR):
        state, _ = _derive_claim_state(claim_dir)
        if state in ("FAIL", "STALE"):
            problems.append((claim_dir.name, state))

    if not problems:
        return EXIT_PASS

    print("falsify guard: logged issues:", file=sys.stderr)
    for name, state in problems:
        print(f"  - {name}: {state}", file=sys.stderr)
    return EXIT_FAIL


def _guard_wrap_mode(cmd_tokens: list[str]) -> int:
    if not cmd_tokens:
        print("falsify guard: no command to wrap after `--`", file=sys.stderr)
        return 1
    try:
        result = subprocess.run(cmd_tokens)
    except FileNotFoundError as e:
        print(f"falsify guard: {e}", file=sys.stderr)
        return 127
    if result.returncode != 0:
        return result.returncode
    return _guard_scan_mode()


def cmd_guard(args: argparse.Namespace) -> int:
    tokens: list[str] = list(args.rest)
    if tokens and tokens[0] == "--":
        return _guard_wrap_mode(tokens[1:])
    if tokens:
        return _guard_text_mode(" ".join(tokens))
    return _guard_scan_mode()


def _gather_claims(base: Path) -> list[dict]:
    if not base.exists():
        return []
    claims: list[dict] = []
    for claim_dir in sorted(base.iterdir()):
        if not claim_dir.is_dir():
            continue
        if not (claim_dir / "spec.yaml").exists():
            continue

        spec_hash: str | None = None
        lock_path = claim_dir / "spec.lock.json"
        if lock_path.exists():
            try:
                lock_data = json.loads(lock_path.read_text())
                h = lock_data.get("spec_hash")
                if isinstance(h, str):
                    spec_hash = h
            except (OSError, json.JSONDecodeError):
                pass

        last_run: str | None = None
        run_dir = _resolve_latest_run(claim_dir)
        if run_dir is not None and run_dir.exists():
            last_run = run_dir.name

        verdict_str: str | None = None
        observed: float | None = None
        verdict_path = claim_dir / "verdict.json"
        if verdict_path.exists():
            try:
                v = json.loads(verdict_path.read_text())
                if isinstance(v, dict):
                    if isinstance(v.get("verdict"), str):
                        verdict_str = v["verdict"]
                    if isinstance(v.get("observed_value"), (int, float)):
                        observed = float(v["observed_value"])
            except (OSError, json.JSONDecodeError):
                pass

        claims.append({
            "name": claim_dir.name,
            "locked": spec_hash is not None,
            "spec_hash": spec_hash,
            "last_run": last_run,
            "verdict": verdict_str,
            "observed_value": observed,
        })
    return claims


_STATS_STALE_DAYS = 7


def _read_metric_name_from_spec(claim_dir: Path) -> str | None:
    try:
        spec = yaml.safe_load((claim_dir / "spec.yaml").read_text())
    except (yaml.YAMLError, OSError):
        return None
    if not isinstance(spec, dict):
        return None
    criteria = spec.get("falsification", {}).get("failure_criteria") or []
    if criteria and isinstance(criteria[0], dict):
        m = criteria[0].get("metric")
        if isinstance(m, str):
            return m
    return None


def _read_kind_from_spec(claim_dir: Path) -> str:
    """Return the spec's optional ``kind`` field (default ``dogfood``).

    The honesty score only counts claims that are about falsify itself
    (``kind: dogfood``). External case studies (``kind: case_study``)
    are excluded — their PASS/FAIL says nothing about whether falsify
    is honest about its own properties.
    """
    try:
        spec = yaml.safe_load((claim_dir / "spec.yaml").read_text())
    except (yaml.YAMLError, OSError):
        return "dogfood"
    if not isinstance(spec, dict):
        return "dogfood"
    kind = spec.get("kind")
    if isinstance(kind, str) and kind.strip():
        return kind.strip()
    return "dogfood"


def _gather_stats_rows(base: Path, name_filter: str | None) -> list[dict]:
    now = datetime.now(timezone.utc)
    rows: list[dict] = []
    for claim_dir in _iter_claim_dirs(base):
        if name_filter and name_filter not in claim_dir.name:
            continue

        state, verdict_data = _derive_claim_state(claim_dir)

        metric: str | None = None
        value: float | None = None
        threshold: float | None = None
        n: int | None = None
        last_run_iso: str | None = None
        age_days: int | None = None

        if isinstance(verdict_data, dict):
            v_metric = verdict_data.get("metric")
            if isinstance(v_metric, str):
                metric = v_metric
            v_value = verdict_data.get("observed_value")
            if isinstance(v_value, (int, float)) and not isinstance(v_value, bool):
                value = float(v_value)
            v_threshold = verdict_data.get("threshold")
            if isinstance(v_threshold, (int, float)) and not isinstance(
                v_threshold, bool
            ):
                threshold = float(v_threshold)
            v_n = verdict_data.get("sample_size")
            if isinstance(v_n, int) and not isinstance(v_n, bool):
                n = v_n
            checked_at = verdict_data.get("checked_at")
            if isinstance(checked_at, str):
                last_run_iso = checked_at
                try:
                    t = datetime.fromisoformat(checked_at)
                    age_days = (now - t).days
                except ValueError:
                    pass

        if metric is None:
            metric = _read_metric_name_from_spec(claim_dir)

        if (
            state in ("PASS", "FAIL", "INCONCLUSIVE")
            and age_days is not None
            and age_days > _STATS_STALE_DAYS
        ):
            state = "STALE"

        rows.append({
            "name": claim_dir.name,
            "state": state,
            "metric": metric,
            "value": value,
            "threshold": threshold,
            "n": n,
            "last_run_iso": last_run_iso,
            "age_days": age_days,
        })
    return rows


_HTML_STATS_STYLE = """\
* { box-sizing: border-box; }
:root {
  --bg: #ffffff;
  --surface: #f6f8fa;
  --fg: #1f2328;
  --muted: #656d76;
  --border: #d1d9e0;
  --pass: #2ea043;
  --fail: #da3633;
  --inconclusive: #d29922;
  --stale: #6e7681;
  --unrun: #8b949e;
}
@media (prefers-color-scheme: dark) {
  :root {
    --bg: #0d1117;
    --surface: #161b22;
    --fg: #e6edf3;
    --muted: #8b949e;
    --border: #30363d;
  }
}
body {
  margin: 0;
  padding: 2rem;
  background: var(--bg);
  color: var(--fg);
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
               "Helvetica Neue", Arial, sans-serif;
  line-height: 1.5;
}
header.page, section.summary, section.cards, footer.page {
  max-width: 1400px;
  margin-left: auto;
  margin-right: auto;
}
header.page { margin-bottom: 1.5rem; }
h1 { margin: 0 0 0.25rem; font-size: 1.5rem; }
.subtitle { color: var(--muted); margin: 0; font-size: 0.9rem; }
section.summary {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  margin-bottom: 1.5rem;
}
.pill {
  display: inline-block;
  padding: 0.25rem 0.75rem;
  border-radius: 9999px;
  background: var(--surface);
  border: 1px solid var(--border);
  font-size: 0.85rem;
  font-weight: 500;
}
.pill.state-PASS { border-color: var(--pass); color: var(--pass); }
.pill.state-FAIL { border-color: var(--fail); color: var(--fail); }
.pill.state-INCONCLUSIVE { border-color: var(--inconclusive); color: var(--inconclusive); }
.pill.state-STALE { border-color: var(--stale); color: var(--stale); }
.pill.state-UNRUN { border-color: var(--unrun); color: var(--unrun); }
section.cards {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 1rem;
}
article.card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-left-width: 4px;
  border-radius: 6px;
  padding: 1rem;
}
article.card.state-PASS { border-left-color: var(--pass); }
article.card.state-FAIL { border-left-color: var(--fail); }
article.card.state-INCONCLUSIVE { border-left-color: var(--inconclusive); }
article.card.state-STALE { border-left-color: var(--stale); }
article.card.state-UNRUN { border-left-color: var(--unrun); }
article.card > header.card-head {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  gap: 0.5rem;
  margin-bottom: 0.5rem;
}
article.card h2 { margin: 0; font-size: 1.05rem; word-break: break-word; }
.badge {
  font-size: 0.7rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  padding: 0.15rem 0.5rem;
  border-radius: 4px;
  color: #ffffff;
  white-space: nowrap;
}
.badge.state-PASS { background: var(--pass); }
.badge.state-FAIL { background: var(--fail); }
.badge.state-INCONCLUSIVE { background: var(--inconclusive); }
.badge.state-STALE { background: var(--stale); }
.badge.state-UNRUN { background: var(--unrun); }
p.claim {
  color: var(--muted);
  font-size: 0.9rem;
  margin: 0.25rem 0 0.75rem;
}
dl {
  margin: 0;
  display: grid;
  grid-template-columns: max-content 1fr;
  column-gap: 0.75rem;
  row-gap: 0.2rem;
  font-size: 0.85rem;
}
dt { color: var(--muted); }
dd { margin: 0; overflow-wrap: anywhere; }
code {
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  font-size: 0.85em;
}
footer.page {
  margin-top: 2rem;
  padding-top: 1rem;
  border-top: 1px solid var(--border);
  color: var(--muted);
  font-size: 0.85rem;
}
footer.page a { color: inherit; }
.empty {
  color: var(--muted);
  font-style: italic;
}
"""


def _truncate_claim(s: str, limit: int = 200) -> str:
    if len(s) <= limit:
        return s
    return s[:limit].rstrip() + "…"


def _age_phrase(age_days: int | None) -> str:
    if age_days is None:
        return "—"
    if age_days <= 0:
        return "today"
    if age_days == 1:
        return "1 day ago"
    return f"{age_days} days ago"


def _enrich_html_row(row: dict, base: Path) -> dict:
    name = row["name"]
    claim_dir = base / name
    claim_text = _read_claim_text(claim_dir) or ""

    spec_hash = ""
    lock_path = claim_dir / "spec.lock.json"
    if lock_path.exists():
        try:
            lock_data = json.loads(lock_path.read_text())
            h = lock_data.get("spec_hash")
            if isinstance(h, str):
                spec_hash = h
        except (OSError, json.JSONDecodeError):
            pass

    direction: str | None = None
    verdict_path = claim_dir / "verdict.json"
    if verdict_path.exists():
        try:
            vd = json.loads(verdict_path.read_text())
            if isinstance(vd, dict):
                d = vd.get("direction")
                if isinstance(d, str):
                    direction = d
        except (OSError, json.JSONDecodeError):
            pass

    return {
        **row,
        "claim_text": claim_text,
        "spec_hash": spec_hash,
        "direction": direction,
    }


def _render_stats_html(rows: list[dict], generated_at_iso: str) -> str:
    counts = {"PASS": 0, "FAIL": 0, "INCONCLUSIVE": 0, "STALE": 0, "UNRUN": 0}
    for r in rows:
        state = r["state"]
        key = state if state in counts else "UNRUN"
        counts[key] += 1

    pills_html = "".join(
        f'      <span class="pill state-{state}">{state}: {count}</span>\n'
        for state, count in counts.items()
    )

    def _cell(value: Any, *, mono: bool = True) -> str:
        if value is None or value == "":
            return "—"
        escaped = html_module.escape(str(value))
        return f"<code>{escaped}</code>" if mono else escaped

    if not rows:
        cards_body = '      <p class="empty">No specs yet — run `falsify init &lt;name&gt;` to start.</p>\n'
    else:
        card_parts = []
        for r in rows:
            name_esc = html_module.escape(r["name"])
            state = r["state"]
            state_esc = html_module.escape(state)
            claim_esc = html_module.escape(_truncate_claim(r.get("claim_text") or ""))
            metric_cell = _cell(r.get("metric"))
            value_cell = _cell(r.get("value"))
            threshold = r.get("threshold")
            direction = r.get("direction")
            if threshold is not None and direction:
                threshold_cell = _cell(f"{direction} {threshold}")
            elif threshold is not None:
                threshold_cell = _cell(threshold)
            else:
                threshold_cell = "—"
            n_cell = _cell(r.get("n"))
            last_run_cell = _cell(r.get("last_run_iso"), mono=False)
            age_cell = html_module.escape(_age_phrase(r.get("age_days")))
            hash_short = (r.get("spec_hash") or "")[:8]
            hash_cell = _cell(hash_short) if hash_short else "—"

            card_parts.append(
                f'      <article class="card state-{state_esc}">\n'
                f'        <header class="card-head">\n'
                f'          <h2>{name_esc}</h2>\n'
                f'          <span class="badge state-{state_esc}">{state_esc}</span>\n'
                f'        </header>\n'
                f'        <p class="claim">{claim_esc if claim_esc else "—"}</p>\n'
                f'        <dl>\n'
                f'          <dt>metric</dt><dd>{metric_cell}</dd>\n'
                f'          <dt>observed</dt><dd>{value_cell}</dd>\n'
                f'          <dt>threshold</dt><dd>{threshold_cell}</dd>\n'
                f'          <dt>n</dt><dd>{n_cell}</dd>\n'
                f'          <dt>last run</dt><dd>{last_run_cell} ({age_cell})</dd>\n'
                f'          <dt>hash</dt><dd>{hash_cell}</dd>\n'
                f'        </dl>\n'
                f'      </article>\n'
            )
        cards_body = "".join(card_parts)

    total = len(rows)
    generated_esc = html_module.escape(generated_at_iso)

    return (
        '<!DOCTYPE html>\n'
        '<html lang="en">\n'
        '<head>\n'
        '<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        '<title>Falsification Engine — Verdict Dashboard</title>\n'
        f'<style>\n{_HTML_STATS_STYLE}</style>\n'
        '</head>\n'
        '<body>\n'
        '  <header class="page">\n'
        '    <h1>Falsification Engine — Verdict Dashboard</h1>\n'
        f'    <p class="subtitle">{total} spec(s) · Generated {generated_esc}</p>\n'
        '  </header>\n'
        '  <section class="summary">\n'
        f'{pills_html}'
        '  </section>\n'
        '  <section class="cards">\n'
        f'{cards_body}'
        '  </section>\n'
        '  <footer class="page">\n'
        '    <p>Generated by <code>falsify stats --html</code> · '
        '<a href="https://github.com/studio-11-co/falsify">falsify</a></p>\n'
        '  </footer>\n'
        '</body>\n'
        '</html>\n'
    )


def _write_stats_output(text: str, output_path: str | None) -> None:
    if output_path:
        Path(output_path).write_text(text)
    else:
        sys.stdout.write(text if text.endswith("\n") else text + "\n")


def cmd_stats(args: argparse.Namespace) -> int:
    rows = _gather_stats_rows(FALSIFY_DIR, args.name)

    if getattr(args, "html", False):
        enriched = [_enrich_html_row(r, FALSIFY_DIR) for r in rows]
        html_text = _render_stats_html(
            enriched, datetime.now(timezone.utc).isoformat()
        )
        _write_stats_output(html_text, getattr(args, "output", None))
        return EXIT_PASS

    if args.json:
        payload = json.dumps(rows, indent=2, sort_keys=True)
        _write_stats_output(payload, getattr(args, "output", None))
        return EXIT_PASS

    counts = {"PASS": 0, "FAIL": 0, "INCONCLUSIVE": 0, "STALE": 0, "UNRUN": 0}
    for r in rows:
        s = r["state"]
        if s in counts:
            counts[s] += 1
        else:
            counts["UNRUN"] += 1

    lines: list[str] = []
    if rows:
        headers = ["NAME", "STATE", "METRIC", "VALUE", "THRESHOLD", "N", "AGE(d)"]
        table: list[list[str]] = [headers]
        for r in rows:
            table.append([
                r["name"],
                r["state"],
                r["metric"] or "-",
                f"{r['value']}" if r["value"] is not None else "-",
                f"{r['threshold']}" if r["threshold"] is not None else "-",
                f"{r['n']}" if r["n"] is not None else "-",
                f"{r['age_days']}" if r["age_days"] is not None else "-",
            ])
        widths = [max(len(row[i]) for row in table) for i in range(len(headers))]
        for row in table:
            lines.append(
                "  ".join(cell.ljust(w) for cell, w in zip(row, widths)).rstrip()
            )
        lines.append("")

    lines.append(
        f"{len(rows)} specs: "
        f"{counts['PASS']} PASS, "
        f"{counts['FAIL']} FAIL, "
        f"{counts['INCONCLUSIVE']} INCONCLUSIVE, "
        f"{counts['STALE']} STALE, "
        f"{counts['UNRUN']} UNRUN"
    )
    output_path = getattr(args, "output", None)
    if output_path:
        Path(output_path).write_text("\n".join(lines) + "\n")
    else:
        for line in lines:
            print(line)
    return EXIT_PASS


def cmd_list(args: argparse.Namespace) -> int:
    claims = _gather_claims(FALSIFY_DIR)

    if args.json:
        print(json.dumps(claims, indent=2, sort_keys=True))
        return EXIT_PASS

    if not claims:
        print("No hypotheses yet. Run `falsify init <name>` to create one.")
        return EXIT_PASS

    headers = ["NAME", "LOCKED", "LAST RUN", "VERDICT", "OBSERVED"]
    rows: list[list[str]] = [headers]
    for c in claims:
        rows.append([
            c["name"],
            c["spec_hash"][:12] if c["spec_hash"] else "-",
            c["last_run"] or "-",
            c["verdict"] or "-",
            f"{c['observed_value']}" if c["observed_value"] is not None else "-",
        ])

    widths = [max(len(row[i]) for row in rows) for i in range(len(headers))]
    for row in rows:
        print("  ".join(cell.ljust(w) for cell, w in zip(row, widths)).rstrip())

    return EXIT_PASS


def _git_repo_root() -> Path | None:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            check=False,
        )
    except (FileNotFoundError, OSError):
        return None
    if result.returncode != 0:
        return None
    path = result.stdout.strip()
    return Path(path) if path else None


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _hook_install(args: argparse.Namespace) -> int:
    repo_root = _git_repo_root()
    if repo_root is None:
        print(
            "falsify hook install: not in a git repository (or git is "
            "not installed)",
            file=sys.stderr,
        )
        return EXIT_BAD_SPEC

    source = repo_root / "hooks" / "commit-msg"
    if not source.exists():
        print(
            f"falsify hook install: source hook missing at {source}",
            file=sys.stderr,
        )
        return EXIT_BAD_SPEC

    hooks_dir = repo_root / ".git" / "hooks"
    hooks_dir.mkdir(parents=True, exist_ok=True)
    target = hooks_dir / "commit-msg"

    if target.exists() or target.is_symlink():
        if target.exists() and _sha256_file(target) == _sha256_file(source):
            print(f"Already installed at {target} (no change)")
            return EXIT_PASS
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        backup = hooks_dir / f"commit-msg.bak.{ts}"
        shutil.move(str(target), str(backup))
        print(f"Backed up existing hook to {backup}")

    shutil.copy2(str(source), str(target))
    target.chmod(0o755)
    print(f"Installed commit-msg guard at {target}")
    return EXIT_PASS


def _hook_uninstall(args: argparse.Namespace) -> int:
    repo_root = _git_repo_root()
    if repo_root is None:
        print(
            "falsify hook uninstall: not in a git repository",
            file=sys.stderr,
        )
        return EXIT_BAD_SPEC

    hooks_dir = repo_root / ".git" / "hooks"
    target = hooks_dir / "commit-msg"
    source = repo_root / "hooks" / "commit-msg"

    if not target.exists():
        print(f"Nothing to uninstall — no hook at {target}")
        return EXIT_PASS

    matches_ours = (
        source.exists() and _sha256_file(target) == _sha256_file(source)
    )
    if matches_ours:
        target.unlink()
        print(f"Removed {target}")
    else:
        print(
            f"Hook at {target} does not match ours — leaving it in place "
            f"(it may be user-authored).",
            file=sys.stderr,
        )

    backups = sorted(
        hooks_dir.glob("commit-msg.bak.*"), reverse=True
    )
    if backups and matches_ours:
        latest = backups[0]
        if args.force:
            shutil.move(str(latest), str(target))
            target.chmod(0o755)
            print(f"Restored previous hook from {latest.name}")
        else:
            print(
                f"Backup found at {latest}. "
                f"Re-run with --force to restore it."
            )

    return EXIT_PASS


def _export_records_for_spec(
    claim_dir: Path, include_runs: bool
) -> list[dict]:
    records: list[dict] = []
    name = claim_dir.name
    spec_path = claim_dir / "spec.yaml"
    lock_path = claim_dir / "spec.lock.json"
    verdict_path = claim_dir / "verdict.json"

    locked_hash = ""
    if lock_path.exists() and spec_path.exists():
        try:
            lock_data = json.loads(lock_path.read_text())
            spec = yaml.safe_load(spec_path.read_text())
        except (yaml.YAMLError, OSError, json.JSONDecodeError):
            spec = None
            lock_data = None

        if isinstance(lock_data, dict) and isinstance(spec, dict):
            h = lock_data.get("spec_hash")
            if isinstance(h, str):
                locked_hash = h
            locked_at = lock_data.get("locked_at")

            snippet: dict = {}
            claim = spec.get("claim")
            if isinstance(claim, str):
                snippet["claim"] = _truncate_claim(claim)
            criteria = (
                spec.get("falsification", {}).get("failure_criteria") or []
            )
            if criteria and isinstance(criteria[0], dict):
                first = criteria[0]
                for k in ("metric", "direction", "threshold"):
                    if k in first:
                        snippet[k] = first[k]

            if isinstance(locked_at, str) and locked_at:
                records.append({
                    "type": "lock",
                    "schema_version": 1,
                    "name": name,
                    "ts": locked_at,
                    "canonical_hash": locked_hash,
                    "spec_snippet": snippet,
                })

    if include_runs:
        runs_dir = claim_dir / "runs"
        if runs_dir.exists():
            for run_dir in sorted(runs_dir.iterdir()):
                if not run_dir.is_dir():
                    continue
                meta_path = run_dir / "run_meta.json"
                if not meta_path.exists():
                    continue
                try:
                    meta = json.loads(meta_path.read_text())
                except (OSError, json.JSONDecodeError):
                    continue
                stdout_path = run_dir / "stdout.txt"
                stdout_sha256 = ""
                stdout_sample = ""
                if stdout_path.exists():
                    try:
                        raw = stdout_path.read_bytes()
                        stdout_sha256 = hashlib.sha256(raw).hexdigest()
                        stdout_sample = raw.decode("utf-8", errors="replace")[:200]
                    except OSError:
                        pass
                ts = meta.get("start")
                if not isinstance(ts, str):
                    continue
                records.append({
                    "type": "run",
                    "schema_version": 1,
                    "name": name,
                    "ts": ts,
                    "duration_s": meta.get("duration_s"),
                    "exit_code": meta.get("returncode"),
                    "stdout_sha256": stdout_sha256,
                    "stdout_sample": stdout_sample,
                })

    if verdict_path.exists():
        try:
            vd = json.loads(verdict_path.read_text())
        except (OSError, json.JSONDecodeError):
            vd = None
        if isinstance(vd, dict):
            ts = vd.get("checked_at")
            if isinstance(ts, str) and ts:
                records.append({
                    "type": "verdict",
                    "schema_version": 1,
                    "name": name,
                    "ts": ts,
                    "state": vd.get("verdict", ""),
                    "metric_value": vd.get("observed_value"),
                    "threshold": vd.get("threshold"),
                    "direction": vd.get("direction", ""),
                    "n": vd.get("sample_size"),
                    "locked_hash": locked_hash,
                })

    return records


def cmd_export(args: argparse.Namespace) -> int:
    all_records: list[dict] = []
    for claim_dir in _iter_claim_dirs(FALSIFY_DIR):
        if args.name and args.name not in claim_dir.name:
            continue
        all_records.extend(
            _export_records_for_spec(claim_dir, args.include_runs)
        )

    if args.since:
        try:
            since_dt = datetime.fromisoformat(args.since)
        except ValueError:
            print(
                f"falsify export: bad --since value {args.since!r} — "
                f"expected ISO 8601 (YYYY-MM-DD or ...Thh:mm:ss+00:00)",
                file=sys.stderr,
            )
            return EXIT_BAD_SPEC
        if since_dt.tzinfo is None:
            since_dt = since_dt.replace(tzinfo=timezone.utc)

        filtered: list[dict] = []
        for r in all_records:
            ts_raw = r.get("ts", "")
            if not isinstance(ts_raw, str) or not ts_raw:
                continue
            try:
                rts = datetime.fromisoformat(ts_raw)
            except ValueError:
                continue
            if rts.tzinfo is None:
                rts = rts.replace(tzinfo=timezone.utc)
            if rts >= since_dt:
                filtered.append(r)
        all_records = filtered

    all_records.sort(
        key=lambda r: (r.get("ts", ""), r.get("type", ""), r.get("name", ""))
    )

    lines = [json.dumps(r, sort_keys=True) for r in all_records]
    output_text = ("\n".join(lines) + "\n") if lines else ""

    if args.output:
        Path(args.output).write_text(output_text)
    else:
        sys.stdout.write(output_text)
    return EXIT_PASS


_VERIFY_REQUIRED: dict[str, set[str]] = {
    "lock": {"name", "ts", "canonical_hash"},
    "run": {"name", "ts", "stdout_sha256"},
    "verdict": {"name", "ts", "state", "locked_hash"},
}


def _verify_collect_findings(
    records: list[tuple[int, dict]],
) -> list[dict]:
    findings: list[dict] = []

    for line_no, r in records:
        t = r.get("type")
        if t not in _VERIFY_REQUIRED:
            findings.append({
                "level": "FAIL",
                "message": f"unknown record type: {t!r}",
                "line": line_no,
            })
            continue
        sv = r.get("schema_version")
        if sv != 1:
            findings.append({
                "level": "WARN",
                "message": f"unknown schema_version: {sv!r}",
                "line": line_no,
            })
        missing = _VERIFY_REQUIRED[t] - set(r.keys())
        if missing:
            findings.append({
                "level": "FAIL",
                "message": f"{t} missing required fields: {sorted(missing)}",
                "line": line_no,
            })

    by_name: dict[str, list[tuple[int, dict]]] = {}
    for line_no, r in records:
        name = r.get("name")
        if not isinstance(name, str):
            continue
        by_name.setdefault(name, []).append((line_no, r))

    for name, group in by_name.items():
        prev_ts: str | None = None
        for line_no, r in group:
            ts = r.get("ts")
            if isinstance(ts, str) and prev_ts is not None and ts < prev_ts:
                findings.append({
                    "level": "FAIL",
                    "message": (
                        f"{name}: timestamp regression "
                        f"({ts!r} < {prev_ts!r})"
                    ),
                    "line": line_no,
                })
            if isinstance(ts, str):
                prev_ts = ts

        seen: set[tuple] = set()
        for line_no, r in group:
            key = (r.get("type"), r.get("ts"))
            if key in seen:
                findings.append({
                    "level": "FAIL",
                    "message": f"{name}: duplicate ({key[0]}, {key[1]})",
                    "line": line_no,
                })
            seen.add(key)

        current_lock_hash: str | None = None
        for line_no, r in group:
            t = r.get("type")
            if t == "lock":
                ch = r.get("canonical_hash")
                if isinstance(ch, str):
                    current_lock_hash = ch
            elif t == "run":
                if current_lock_hash is None:
                    findings.append({
                        "level": "FAIL",
                        "message": f"{name}: run before any lock",
                        "line": line_no,
                    })
            elif t == "verdict":
                lh = r.get("locked_hash")
                if current_lock_hash is None:
                    findings.append({
                        "level": "FAIL",
                        "message": f"{name}: verdict before any lock",
                        "line": line_no,
                    })
                elif lh != current_lock_hash:
                    findings.append({
                        "level": "FAIL",
                        "message": (
                            f"{name}: verdict locked_hash does not match "
                            f"preceding lock canonical_hash "
                            f"({lh!r} vs {current_lock_hash!r})"
                        ),
                        "line": line_no,
                    })

    return findings


def cmd_verify(args: argparse.Namespace) -> int:
    path = Path(args.jsonl_path)
    if not path.exists():
        print(
            f"falsify verify: file not found: {path}",
            file=sys.stderr,
        )
        return EXIT_BAD_SPEC
    try:
        content = path.read_text()
    except OSError as e:
        print(f"falsify verify: cannot read {path}: {e}", file=sys.stderr)
        return EXIT_BAD_SPEC

    records: list[tuple[int, dict]] = []
    for idx, line in enumerate(content.splitlines(), start=1):
        if not line.strip():
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError as e:
            print(
                f"falsify verify: line {idx}: invalid JSON — {e}",
                file=sys.stderr,
            )
            return EXIT_BAD_SPEC
        if not isinstance(obj, dict):
            print(
                f"falsify verify: line {idx}: expected object, got "
                f"{type(obj).__name__}",
                file=sys.stderr,
            )
            return EXIT_BAD_SPEC
        records.append((idx, obj))

    findings = _verify_collect_findings(records)

    if content and not content.endswith("\n"):
        findings.append({
            "level": "WARN",
            "message": "file does not end with a newline",
            "line": len(content.splitlines()),
        })

    by_name: dict[str, dict] = {}
    line_to_name: dict[int, str] = {}
    for line_no, r in records:
        name = r.get("name")
        if not isinstance(name, str):
            continue
        line_to_name[line_no] = name
        spec = by_name.setdefault(
            name,
            {
                "name": name,
                "records": 0,
                "lock": 0,
                "run": 0,
                "verdict": 0,
                "findings": [],
            },
        )
        spec["records"] += 1
        t = r.get("type")
        if t in ("lock", "run", "verdict"):
            spec[t] += 1

    for f in findings:
        name = line_to_name.get(f.get("line"))
        if name and name in by_name:
            by_name[name]["findings"].append(f)

    for spec in by_name.values():
        levels = {x["level"] for x in spec["findings"]}
        if "FAIL" in levels:
            spec["status"] = "FAIL"
        elif "WARN" in levels:
            spec["status"] = "WARN"
        else:
            spec["status"] = "OK"

    has_fail = any(f["level"] == "FAIL" for f in findings)
    has_warn = any(f["level"] == "WARN" for f in findings)
    treat_warn_as_fail = args.strict and has_warn
    invalid = has_fail or treat_warn_as_fail
    verdict_label = "INVALID" if invalid else "VALID"

    spec_list = sorted(by_name.values(), key=lambda s: s["name"])
    summary = {
        "ok": sum(1 for s in spec_list if s["status"] == "OK"),
        "warn": sum(1 for s in spec_list if s["status"] == "WARN"),
        "fail": sum(1 for s in spec_list if s["status"] == "FAIL"),
    }

    if args.json:
        payload = {
            "verdict": verdict_label,
            "summary": summary,
            "specs": [
                {
                    "name": s["name"],
                    "status": s["status"],
                    "records": s["records"],
                    "findings": s["findings"],
                }
                for s in spec_list
            ],
            "findings": findings,
        }
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(f"verify {path}: {verdict_label}")
        for s in spec_list:
            print(
                f"  {s['name']}: {s['status']} "
                f"({s['lock']} lock, {s['run']} run, {s['verdict']} verdict)"
            )
            for f in s["findings"]:
                print(f"    [{f['level']}] line {f['line']}: {f['message']}")
        orphan = [f for f in findings if line_to_name.get(f.get("line")) is None]
        for f in orphan:
            print(f"  [{f['level']}] line {f.get('line', '?')}: {f['message']}")
        print(
            f"Summary: {summary['ok']} OK, {summary['warn']} WARN, "
            f"{summary['fail']} FAIL → {verdict_label}"
        )

    return EXIT_FAIL if invalid else EXIT_PASS


def _compute_honesty_score(rows: list[dict]) -> tuple[float, dict[str, int]]:
    """Apply the honesty rubric to stats rows.

    Returns ``(score_clamped_to_[0,1], counts)`` where counts is a
    breakdown across the seven possible states. Rubric::

        score = (pass_weight_sum + unlocked_penalty) / max(total, 1)

        pass weights:
          PASS         -> 1.0
          INCONCLUSIVE -> 0.5
          FAIL/STALE/UNRUN -> 0.0
          UNLOCKED     -> -1.0 (penalty applied directly to numerator)
    """
    counts = {
        "PASS": 0,
        "FAIL": 0,
        "INCONCLUSIVE": 0,
        "STALE": 0,
        "UNRUN": 0,
        "UNLOCKED": 0,
    }
    for r in rows:
        state = r["state"]
        if state in counts:
            counts[state] += 1
        elif state == "UNKNOWN":
            counts["UNLOCKED"] += 1

    total = sum(counts.values())
    if total == 0:
        return 0.0, counts

    weight_sum = (
        1.0 * counts["PASS"]
        + 0.5 * counts["INCONCLUSIVE"]
        - 1.0 * counts["UNLOCKED"]
    )
    raw = weight_sum / total
    return max(0.0, min(1.0, raw)), counts


def _score_status(score: float, threshold: float) -> str:
    if score >= threshold:
        return "ok"
    if score >= threshold * 0.5:
        return "warn"
    return "fail"


_SCORE_COLORS = {"ok": "brightgreen", "warn": "yellow", "fail": "red"}
_SCORE_COLOR_HEX = {
    "brightgreen": "#4c1",
    "yellow": "#dfb317",
    "red": "#e05d44",
}


def _score_text_line(score: float, counts: dict[str, int]) -> str:
    total = sum(counts.values())
    notes: list[str] = []
    for state, label in (
        ("STALE", "stale"),
        ("UNRUN", "unrun"),
        ("INCONCLUSIVE", "inconclusive"),
        ("UNLOCKED", "unlocked"),
        ("FAIL", "fail"),
    ):
        if counts[state]:
            notes.append(f"{counts[state]} {label}")
    notes_str = (", " + ", ".join(notes)) if notes else ""
    return (
        f"honesty: {score:.2f} ({counts['PASS']}/{total} passing{notes_str})"
    )


def _score_svg(score: float, color: str) -> str:
    label = "falsify"
    value = f"{score:.2f}"
    safe_value = html_module.escape(value, quote=True)
    label_w = 52
    value_w = 40
    total_w = label_w + value_w
    label_x = label_w / 2
    value_x = label_w + value_w / 2
    color_hex = _SCORE_COLOR_HEX[color]
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{total_w}" height="20">\n'
        '  <linearGradient id="b" x2="0" y2="100%">\n'
        '    <stop offset="0" stop-color="#bbb" stop-opacity=".1"/>\n'
        '    <stop offset="1" stop-opacity=".1"/>\n'
        '  </linearGradient>\n'
        f'  <mask id="a"><rect width="{total_w}" height="20" rx="3" fill="#fff"/></mask>\n'
        '  <g mask="url(#a)">\n'
        f'    <path fill="#555" d="M0 0h{label_w}v20H0z"/>\n'
        f'    <path fill="{color_hex}" d="M{label_w} 0h{value_w}v20H{label_w}z"/>\n'
        f'    <path fill="url(#b)" d="M0 0h{total_w}v20H0z"/>\n'
        '  </g>\n'
        '  <g fill="#fff" text-anchor="middle" '
        'font-family="DejaVu Sans,Verdana,Geneva,sans-serif" font-size="11">\n'
        f'    <text x="{label_x}" y="14">{label}</text>\n'
        f'    <text x="{value_x}" y="14">{safe_value}</text>\n'
        '  </g>\n'
        '</svg>\n'
    )


def cmd_score(args: argparse.Namespace) -> int:
    """Aggregate a single 'honesty score' across all claims.

    See :func:`_compute_honesty_score` for the rubric. Output formats:

    - ``text``    — one human line.
    - ``json``    — full breakdown plus status.
    - ``shields`` — shields.io endpoint v1 JSON.
    - ``svg``     — minimal flat-style two-section badge.

    Status thresholds: ``ok`` if ``score >= threshold``, ``warn`` if
    ``score >= threshold * 0.5``, ``fail`` otherwise. Exit ``10`` on
    ``fail``; ``warn`` exits ``0`` unless ``--strict``.
    """
    rows = _gather_stats_rows(FALSIFY_DIR, name_filter=None)
    scope = getattr(args, "scope", "dogfood") or "dogfood"
    if scope != "all":
        rows = [
            r
            for r in rows
            if _read_kind_from_spec(FALSIFY_DIR / r["name"]) == scope
        ]
    score, counts = _compute_honesty_score(rows)
    threshold = args.threshold
    status = _score_status(score, threshold)
    color = _SCORE_COLORS[status]
    total = sum(counts.values())

    fmt = args.format
    if fmt == "text":
        body = _score_text_line(score, counts) + "\n"
    elif fmt == "json":
        payload = {
            "score": round(score, 4),
            "total": total,
            "pass": counts["PASS"],
            "fail": counts["FAIL"],
            "inconclusive": counts["INCONCLUSIVE"],
            "stale": counts["STALE"],
            "unrun": counts["UNRUN"],
            "unlocked": counts["UNLOCKED"],
            "threshold": threshold,
            "status": status,
        }
        body = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    elif fmt == "shields":
        payload = {
            "schemaVersion": 1,
            "label": "falsify",
            "message": f"{score:.2f}",
            "color": color,
        }
        body = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    elif fmt == "svg":
        body = _score_svg(score, color)
    else:
        print(f"falsify score: unknown format {fmt!r}", file=sys.stderr)
        return EXIT_BAD_SPEC

    if args.output:
        Path(args.output).write_text(body)
    else:
        sys.stdout.write(body)

    if status == "fail":
        return EXIT_FAIL
    if status == "warn" and args.strict:
        return EXIT_FAIL
    return EXIT_PASS


_TREND_BLOCKS_UNI = "▁▂▃▄▅▆▇█"
_TREND_BLOCKS_ASCII = "_.oO#"


def _trend_collect_records(claim_dir: Path) -> list[dict]:
    """Walk the claim's runs/ dir, return verdict-bearing records in
    chronological order (run dir name is a sortable UTC timestamp)."""
    runs_dir = claim_dir / "runs"
    if not runs_dir.exists():
        return []
    out: list[dict] = []
    for run_dir in sorted(runs_dir.iterdir()):
        if not run_dir.is_dir():
            continue
        verdict_path = run_dir / "verdict.json"
        if not verdict_path.exists():
            continue
        try:
            vd = json.loads(verdict_path.read_text())
        except (OSError, json.JSONDecodeError):
            continue
        val = vd.get("observed_value") if isinstance(vd, dict) else None
        if not isinstance(val, (int, float)) or isinstance(val, bool):
            continue

        spec_hash: str | None = None
        lock_path = run_dir / "spec.lock.json"
        if lock_path.exists():
            try:
                lock_data = json.loads(lock_path.read_text())
                h = lock_data.get("spec_hash") if isinstance(lock_data, dict) else None
                if isinstance(h, str):
                    spec_hash = h
            except (OSError, json.JSONDecodeError):
                pass

        out.append({
            "run_id": run_dir.name,
            "timestamp": (
                vd.get("checked_at")
                if isinstance(vd.get("checked_at"), str)
                else run_dir.name
            ),
            "value": float(val),
            "n": vd.get("sample_size"),
            "verdict": vd.get("verdict", "UNKNOWN"),
            "spec_hash": spec_hash,
        })
    return out


def _trend_resample(values: list[float], width: int) -> list[float]:
    n = len(values)
    if n == 0 or width <= 0:
        return []
    return [values[int(i * n / width)] for i in range(width)]


def _trend_sparkline(values: list[float], width: int, ascii_mode: bool) -> str:
    chars = _TREND_BLOCKS_ASCII if ascii_mode else _TREND_BLOCKS_UNI
    if not values:
        return ""
    lo, hi = min(values), max(values)
    span = (hi - lo) if hi > lo else 1.0
    n_levels = len(chars)
    sampled = _trend_resample(values, width)
    out = []
    for v in sampled:
        idx = int((v - lo) / span * n_levels)
        idx = min(n_levels - 1, max(0, idx))
        out.append(chars[idx])
    return "".join(out)


def _trend_overlay(
    values: list[float],
    threshold: float | None,
    direction: str | None,
    width: int,
) -> tuple[str, str]:
    if (
        threshold is None
        or direction is None
        or not isinstance(threshold, (int, float))
    ):
        return " " * width, "threshold: unknown"

    lo, hi = min(values), max(values)
    if lo <= threshold <= hi:
        sampled = _trend_resample(values, width)
        chars = []
        for v in sampled:
            if direction == "above":
                fails = v <= threshold
            elif direction == "below":
                fails = v >= threshold
            elif direction == "equals":
                fails = abs(v - threshold) > 1e-9
            else:
                fails = False
            chars.append("T" if fails else " ")
        return "".join(chars), f"threshold={threshold} (shown)"

    if threshold > hi:
        return " " * width, f"threshold={threshold} (off-chart, above)"
    return " " * width, f"threshold={threshold} (off-chart, below)"


def _trend_classify(values: list[float], direction: str | None) -> str:
    n = len(values)
    if n < 2:
        return "flat"
    third = max(1, n // 3)
    first_mean = sum(values[:third]) / third
    last_mean = sum(values[-third:]) / third
    delta = last_mean - first_mean
    lo, hi = min(values), max(values)
    spread = (hi - lo) if hi > lo else 0.0
    if spread <= 0:
        return "flat"
    pct = abs(delta) / spread
    if pct < 0.02:
        return "flat"
    if direction == "above":
        going_bad = delta < 0
    elif direction == "below":
        going_bad = delta > 0
    else:
        return "mixed"
    if pct > 0.05:
        return "degrading" if going_bad else "improving"
    return "mixed"


def cmd_trend(args: argparse.Namespace) -> int:
    name = args.claim_name
    claim_dir = FALSIFY_DIR / name
    if not claim_dir.exists() or not (claim_dir / "spec.yaml").exists():
        print(
            f"falsify trend: claim {name!r} not found under "
            f".falsify/ (try `falsify list`)",
            file=sys.stderr,
        )
        return EXIT_BAD_SPEC

    threshold: float | None = None
    direction: str | None = None
    try:
        spec = yaml.safe_load((claim_dir / "spec.yaml").read_text())
    except (yaml.YAMLError, OSError):
        spec = None
    if isinstance(spec, dict):
        fc = (spec.get("falsification") or {}).get("failure_criteria") or []
        if fc and isinstance(fc[0], dict):
            t = fc[0].get("threshold")
            if isinstance(t, (int, float)) and not isinstance(t, bool):
                threshold = float(t)
            d = fc[0].get("direction")
            if isinstance(d, str):
                direction = d

    all_records = _trend_collect_records(claim_dir)
    total = len(all_records)
    last_cap = min(max(1, args.last or 20), 200)
    records = all_records[-last_cap:]
    shown = len(records)

    if args.json:
        values = [r["value"] for r in records]
        summary: dict[str, Any] = {
            "shown": shown,
            "total": total,
            "threshold": threshold,
            "direction": direction,
        }
        if values:
            summary.update({
                "min": min(values),
                "max": max(values),
                "mean": sum(values) / len(values),
                "trend": _trend_classify(values, direction),
                "latest_verdict": records[-1]["verdict"],
            })
        print(json.dumps(
            {"claim": name, "records": records, "summary": summary},
            indent=2,
            sort_keys=True,
        ))
        return EXIT_PASS

    print(f"claim: {name}")
    if threshold is not None:
        print(f"threshold: {threshold} (direction: {direction})")
    print(f"runs: {shown} shown (of {total})")
    print()

    if shown < 2:
        print(f"not enough runs for a trend (need >= 2, have {shown})")
        return EXIT_PASS

    values = [r["value"] for r in records]
    lo, hi = min(values), max(values)
    width = max(1, args.width or 40)

    print(_trend_sparkline(values, width, ascii_mode=args.ascii))
    overlay, caption = _trend_overlay(values, threshold, direction, width)
    print(overlay)
    print(caption)
    print()

    first, last = records[0], records[-1]
    mean_val = sum(values) / len(values)
    classification = _trend_classify(values, direction)

    print(f"first: {first['value']} @ {first['timestamp']} ({first['verdict']})")
    print(f"last:  {last['value']} @ {last['timestamp']} ({last['verdict']})")
    print(f"min:   {lo}")
    print(f"max:   {hi}")
    print(f"mean:  {mean_val}")
    print(f"latest verdict: {last['verdict']}")
    print(f"trend: {classification}")
    return EXIT_PASS


def _ago(ts_iso: str | None) -> str:
    """Return a compact relative age: 'just now', '2m ago', '3h ago', '5d ago'."""
    if not isinstance(ts_iso, str) or not ts_iso:
        return "unknown"
    try:
        then = datetime.fromisoformat(ts_iso)
    except ValueError:
        return "unknown"
    if then.tzinfo is None:
        then = then.replace(tzinfo=timezone.utc)
    secs = (datetime.now(timezone.utc) - then).total_seconds()
    if secs < 0:
        return "in the future"
    if secs < 60:
        return "just now"
    if secs < 3600:
        return f"{int(secs // 60)}m ago"
    if secs < 86400:
        return f"{int(secs // 3600)}h ago"
    return f"{int(secs // 86400)}d ago"


def _why_state_narrative(
    state: str,
    spec: Any,
    verdict_data: dict | None,
    stored_hash: str | None,
    current_hash: str | None,
) -> tuple[str, str, dict]:
    failure_criteria: list = []
    minimum_sample_size = None
    if isinstance(spec, dict):
        f = spec.get("falsification", {}) or {}
        failure_criteria = f.get("failure_criteria") or []
        minimum_sample_size = f.get("minimum_sample_size")

    first = failure_criteria[0] if failure_criteria else {}
    metric_name = first.get("metric") if isinstance(first, dict) else None
    threshold = first.get("threshold") if isinstance(first, dict) else None
    direction = first.get("direction") if isinstance(first, dict) else None

    value = None
    n = None
    if isinstance(verdict_data, dict):
        value = verdict_data.get("observed_value")
        n = verdict_data.get("sample_size")

    if state == "PASS":
        op = {"above": ">", "below": "<", "equals": "≈"}.get(direction or "", "?")
        reasoning = (
            f"metric {metric_name} = {value} {op} threshold {threshold} "
            f"({n} samples)"
            if n is not None
            else f"metric {metric_name} = {value} {op} threshold {threshold}"
        )
        next_action = "none — the claim is honestly passing."
        details = {
            "metric": metric_name,
            "value": value,
            "threshold": threshold,
            "direction": direction,
            "n": n,
        }
    elif state == "FAIL":
        reasoning = (
            f"metric {metric_name} = {value} violates threshold "
            f"{threshold} (direction: {direction})"
        )
        next_action = (
            "either accept the failure, or diagnose the regression. "
            "Do NOT silently lower the threshold — if the claim itself "
            "is wrong, relock explicitly with `falsify lock <spec> "
            "--force` after editing. A relock creates a new hash and "
            "shows up in the audit trail."
        )
        details = {
            "metric": metric_name,
            "value": value,
            "threshold": threshold,
            "direction": direction,
        }
    elif state == "INCONCLUSIVE":
        vd = verdict_data or {}
        actual_n = vd.get("sample_size")
        min_n = vd.get("minimum_sample_size", minimum_sample_size)
        reasoning = (
            f"sample size {actual_n} is below minimum {min_n}; "
            f"verdict is indeterminate."
        )
        next_action = (
            "collect more data, or lower minimum_sample_size with an "
            "explicit relock."
        )
        details = {"sample_size": actual_n, "minimum_sample_size": min_n}
    elif state == "STALE":
        cur_short = (current_hash or "?")[:12]
        stored_short = (stored_hash or "?")[:12]
        reasoning = (
            f"the spec has been edited (sha256:{cur_short}) but no run "
            f"exists against this hash. Last run was against "
            f"sha256:{stored_short}."
        )
        next_action = (
            "`falsify run <name>` to produce a fresh verdict against "
            "the current spec."
        )
        details = {"stored_hash": stored_hash, "current_hash": current_hash}
    elif state == "UNRUN":
        short = (stored_hash or "?")[:12]
        reasoning = (
            f"the spec is locked (sha256:{short}) but has never been "
            f"executed."
        )
        next_action = "`falsify run <name>`"
        details = {"stored_hash": stored_hash}
    elif state == "UNLOCKED":
        reasoning = (
            "the spec exists but no spec.lock.json — it has not been "
            "committed-to yet. Running now would violate pre-registration."
        )
        next_action = "`falsify lock <name>`, then `falsify run <name>`."
        details = {}
    else:
        reasoning = f"state is {state} — inspect manually"
        next_action = "run `falsify doctor` for diagnostics."
        details = {}

    return reasoning, next_action, details


def _why_recent_runs(claim_dir: Path, limit: int = 5) -> list[dict]:
    runs_dir = claim_dir / "runs"
    if not runs_dir.exists():
        return []
    run_dirs = sorted(
        (p for p in runs_dir.iterdir() if p.is_dir()),
        key=lambda p: p.name,
        reverse=True,
    )
    out: list[dict] = []
    for rd in run_dirs[:limit]:
        entry: dict = {"run_id": rd.name}
        vp = rd / "verdict.json"
        if vp.exists():
            try:
                vd = json.loads(vp.read_text())
                entry["value"] = vd.get("observed_value")
                entry["n"] = vd.get("sample_size")
                entry["checked_at"] = vd.get("checked_at")
            except (OSError, json.JSONDecodeError):
                pass
        mp = rd / "run_meta.json"
        if mp.exists() and "checked_at" not in entry:
            try:
                meta = json.loads(mp.read_text())
                entry["checked_at"] = meta.get("start")
            except (OSError, json.JSONDecodeError):
                pass
        out.append(entry)
    return out


def _compute_why(name: str) -> dict:
    claim_dir = FALSIFY_DIR / name
    spec_path = claim_dir / "spec.yaml"

    if not spec_path.exists():
        claims_hint = ""
        claims_path = Path("claims") / name
        if claims_path.exists() and (claims_path / "spec.yaml").exists():
            claims_hint = (
                f" Note: claims/{name}/ exists but is not mirrored into "
                f".falsify/{name}/ yet; re-run `falsify init --template` "
                f"or copy spec.yaml into place."
            )
        return {
            "claim": name,
            "state": "UNKNOWN",
            "reasoning": (
                f"no claim named {name!r} exists. Scanned .falsify/ "
                f"and ./claims/.{claims_hint}"
            ),
            "locked": None,
            "last_run": None,
            "next_action": (
                "`falsify list` to see known claims, or "
                "`falsify init --template <type>` to scaffold one."
            ),
            "details": {},
            "recent_runs": [],
        }

    state, verdict_data = _derive_claim_state(claim_dir)

    try:
        spec = yaml.safe_load(spec_path.read_text())
    except (yaml.YAMLError, OSError):
        spec = None

    lock_data: dict | None = None
    lock_path = claim_dir / "spec.lock.json"
    if lock_path.exists():
        try:
            lock_data = json.loads(lock_path.read_text())
        except (OSError, json.JSONDecodeError):
            pass

    stored_hash = None
    locked_at = None
    if isinstance(lock_data, dict):
        h = lock_data.get("spec_hash")
        if isinstance(h, str):
            stored_hash = h
        la = lock_data.get("locked_at")
        if isinstance(la, str):
            locked_at = la

    current_hash = None
    if isinstance(spec, dict):
        try:
            current_hash = hashlib.sha256(
                _canonicalize(spec).encode("utf-8")
            ).hexdigest()
        except Exception:
            pass

    last_run_iso = None
    run_dir = _resolve_latest_run(claim_dir)
    if run_dir is not None and run_dir.exists():
        meta_path = run_dir / "run_meta.json"
        if meta_path.exists():
            try:
                meta = json.loads(meta_path.read_text())
                lr = meta.get("start")
                if isinstance(lr, str):
                    last_run_iso = lr
            except (OSError, json.JSONDecodeError):
                pass

    reasoning, next_action, extras = _why_state_narrative(
        state, spec, verdict_data, stored_hash, current_hash,
    )

    locked = (
        {"hash": stored_hash, "locked_at": locked_at}
        if stored_hash is not None
        else None
    )
    details = {"stored_hash": stored_hash, "current_hash": current_hash}
    details.update(extras)

    return {
        "claim": name,
        "state": state,
        "reasoning": reasoning,
        "locked": locked,
        "last_run": last_run_iso,
        "next_action": next_action,
        "details": details,
        "recent_runs": _why_recent_runs(claim_dir),
    }


def cmd_why(args: argparse.Namespace) -> int:
    info = _compute_why(args.claim_name)
    verbose = bool(getattr(args, "verbose", False))

    if args.json:
        payload = {
            "claim": info["claim"],
            "state": info["state"],
            "reasoning": info["reasoning"],
            "locked": info["locked"],
            "last_run": info["last_run"],
            "next_action": info["next_action"],
            "details": info["details"],
        }
        if verbose:
            payload["recent_runs"] = info["recent_runs"]
        print(json.dumps(payload, indent=2, sort_keys=True))
        return EXIT_PASS

    lines = [
        f"claim: {info['claim']}",
        f"state: {info['state']}",
        f"reasoning: {info['reasoning']}",
    ]
    locked = info["locked"]
    if locked:
        h = locked["hash"]
        la = locked["locked_at"]
        if verbose:
            lines.append(f"locked: yes (sha256:{h}, locked_at {la})")
        else:
            lines.append(f"locked: yes (sha256:{h[:12]}, {_ago(la)})")
    else:
        lines.append("locked: no")

    last_run = info["last_run"]
    if last_run:
        if verbose:
            lines.append(f"last run: {last_run}")
        else:
            lines.append(f"last run: {last_run} ({_ago(last_run)})")
    else:
        lines.append("last run: never")

    lines.append(f"next action: {info['next_action']}")

    if verbose and info["recent_runs"]:
        lines.append("recent runs:")
        for r in info["recent_runs"]:
            ts = r.get("checked_at") or "?"
            val = r.get("value", "?")
            n = r.get("n", "?")
            lines.append(
                f"  - {r['run_id']}: value={val}, n={n}, ts={ts}"
            )

    for line in lines:
        print(line)

    return EXIT_PASS


def cmd_version(args: argparse.Namespace) -> int:
    if args.json:
        print(json.dumps({"name": "falsify", "version": __version__}))
    else:
        print(f"falsify {__version__}")
    return EXIT_PASS


def _doctor_env_checks() -> list[dict]:
    out: list[dict] = []

    pyver = sys.version_info
    pv_str = platform.python_version()
    if (pyver.major, pyver.minor) >= (3, 11):
        out.append({
            "level": "OK",
            "message": f"Python version: {pv_str}",
            "detail": None,
        })
    else:
        out.append({
            "level": "WARN",
            "message": f"Python version: {pv_str} (project targets 3.11+)",
            "detail": None,
        })

    out.append({
        "level": "OK",
        "message": f"pyyaml importable: {yaml.__version__}",
        "detail": None,
    })

    repo_root = _git_repo_root()
    if repo_root is None:
        out.append({
            "level": "WARN",
            "message": "Not in a git repository (or git not installed)",
            "detail": None,
        })
        return out

    out.append({
        "level": "OK",
        "message": f"Git repo: {repo_root}",
        "detail": None,
    })

    source_hook = repo_root / "hooks" / "commit-msg"
    if source_hook.exists():
        out.append({
            "level": "OK",
            "message": "hooks/commit-msg source present",
            "detail": None,
        })
    else:
        out.append({
            "level": "WARN",
            "message": f"hooks/commit-msg missing at {source_hook}",
            "detail": None,
        })

    installed = repo_root / ".git" / "hooks" / "commit-msg"
    if not installed.exists():
        out.append({
            "level": "INFO",
            "message": "commit-msg hook not installed",
            "detail": "run `falsify hook install` to enable the guard",
        })
    elif source_hook.exists():
        if _sha256_file(installed) == _sha256_file(source_hook):
            out.append({
                "level": "OK",
                "message": "commit-msg hook installed and matches source",
                "detail": None,
            })
        else:
            out.append({
                "level": "WARN",
                "message": "Hook installed but hash mismatch with hooks/commit-msg",
                "detail": "re-run `falsify hook install` to refresh",
            })
    else:
        out.append({
            "level": "INFO",
            "message": "commit-msg hook installed; source missing, can't verify",
            "detail": None,
        })
    return out


def _doctor_spec_checks() -> list[dict]:
    out: list[dict] = []
    try:
        schema = _load_schema()
    except (yaml.YAMLError, OSError, FileNotFoundError):
        schema = None

    now = datetime.now(timezone.utc)
    for claim_dir in _iter_claim_dirs(FALSIFY_DIR):
        name = claim_dir.name
        spec_path = claim_dir / "spec.yaml"
        lock_path = claim_dir / "spec.lock.json"
        verdict_path = claim_dir / "verdict.json"

        try:
            spec = yaml.safe_load(spec_path.read_text())
        except (yaml.YAMLError, OSError) as e:
            out.append({
                "level": "FAIL",
                "message": f"{name}: spec.yaml failed to parse",
                "detail": str(e),
            })
            continue

        if schema is not None:
            errors: list[str] = []
            _validate_against_schema(spec, schema, "", errors)
            if errors:
                out.append({
                    "level": "FAIL",
                    "message": f"{name}: spec.yaml failed schema validation",
                    "detail": errors[0],
                })
                continue

        out.append({
            "level": "OK",
            "message": f"{name}: spec.yaml valid",
            "detail": None,
        })

        if not lock_path.exists():
            out.append({
                "level": "INFO",
                "message": f"{name}: not locked yet",
                "detail": None,
            })
            continue

        if not verdict_path.exists():
            out.append({
                "level": "INFO",
                "message": f"{name}: locked but not run",
                "detail": None,
            })
            continue

        try:
            verdict_data = json.loads(verdict_path.read_text())
        except (OSError, json.JSONDecodeError) as e:
            out.append({
                "level": "WARN",
                "message": f"{name}: verdict.json unreadable",
                "detail": str(e),
            })
            continue

        state = verdict_data.get("verdict", "UNKNOWN")
        out.append({
            "level": "OK" if state == "PASS" else "INFO",
            "message": f"{name}: last verdict {state}",
            "detail": None,
        })

        checked_at = verdict_data.get("checked_at")
        if isinstance(checked_at, str):
            try:
                t = datetime.fromisoformat(checked_at)
                age_days = (now - t).days
                if age_days > 7:
                    out.append({
                        "level": "WARN",
                        "message": f"{name}: last run is {age_days} days old (stale)",
                        "detail": None,
                    })
            except ValueError:
                pass

    return out


def _doctor_workflow_check() -> list[dict]:
    workflow = Path(".github/workflows/falsify.yml")
    if not workflow.exists():
        return [{
            "level": "INFO",
            "message": "No CI workflow at .github/workflows/falsify.yml",
            "detail": None,
        }]
    try:
        yaml.safe_load(workflow.read_text())
    except yaml.YAMLError as e:
        return [{
            "level": "WARN",
            "message": "CI workflow present but not valid YAML",
            "detail": str(e),
        }]
    return [{
        "level": "OK",
        "message": "CI workflow parses",
        "detail": None,
    }]


def cmd_doctor(args: argparse.Namespace) -> int:
    checks: list[dict] = []
    if not args.specs_only:
        checks.extend(_doctor_env_checks())
    checks.extend(_doctor_spec_checks())
    if not args.specs_only:
        checks.extend(_doctor_workflow_check())

    summary = {"ok": 0, "warn": 0, "fail": 0, "info": 0}
    for c in checks:
        summary[c["level"].lower()] = summary.get(c["level"].lower(), 0) + 1

    if args.json:
        print(json.dumps(
            {"checks": checks, "summary": summary},
            indent=2,
            sort_keys=True,
        ))
    else:
        for c in checks:
            print(f"[{c['level']}] {c['message']}")
            if c.get("detail"):
                print(f"       {c['detail']}")
        print()
        print(
            f"Summary: {summary['ok']} OK, {summary['warn']} WARN, "
            f"{summary['fail']} FAIL, {summary['info']} INFO"
        )

    return EXIT_BAD_SPEC if summary["fail"] > 0 else EXIT_PASS


def cmd_hook(args: argparse.Namespace) -> int:
    if args.action == "install":
        return _hook_install(args)
    if args.action == "uninstall":
        return _hook_uninstall(args)
    print(f"falsify hook: unknown action {args.action!r}", file=sys.stderr)
    return EXIT_BAD_SPEC


_BENCH_DEFAULT_COMMANDS = ("--help", "--version", "list", "stats", "score")
_BENCH_MAX_RUNS = 100


def _bench_parse_commands(csv_str: str | None) -> list[str]:
    """Split the --commands CSV; fall back to the built-in default set."""
    if csv_str is None:
        return list(_BENCH_DEFAULT_COMMANDS)
    items = [chunk.strip() for chunk in csv_str.split(",")]
    return [item for item in items if item]


def _bench_stats(samples_ms: list[float]) -> dict[str, float]:
    """min / median / p95 / max / mean / stddev over a list of ms samples.

    p95 uses linear interpolation on sorted samples so small-n samples
    behave intuitively ([10,20,30,40,50] → 48). stddev is population
    stddev — single-element samples therefore report 0.
    """
    if not samples_ms:
        zero = 0.0
        return {
            "min_ms": zero, "median_ms": zero, "p95_ms": zero,
            "max_ms": zero, "mean_ms": zero, "stddev_ms": zero,
        }
    sorted_ms = sorted(samples_ms)
    n = len(sorted_ms)
    if n == 1:
        p95 = sorted_ms[0]
    else:
        idx = (n - 1) * 0.95
        lo = int(idx)
        hi = min(lo + 1, n - 1)
        frac = idx - lo
        p95 = sorted_ms[lo] + frac * (sorted_ms[hi] - sorted_ms[lo])
    return {
        "min_ms": round(sorted_ms[0], 4),
        "median_ms": round(statistics.median(sorted_ms), 4),
        "p95_ms": round(p95, 4),
        "max_ms": round(sorted_ms[-1], 4),
        "mean_ms": round(statistics.fmean(sorted_ms), 4),
        "stddev_ms": round(statistics.pstdev(sorted_ms), 4),
    }


def _bench_format_table(
    results: list[dict], runs: int, warmup: int
) -> str:
    """Render a bench result set as an aligned-column text table."""
    rows_data = sorted(results, key=lambda r: r["stats"]["median_ms"])
    header = ["command", "min", "median", "p95", "max", "mean", "stddev", "n"]
    table: list[list[str]] = [header]
    for r in rows_data:
        s = r["stats"]
        table.append([
            r["command"],
            f"{s['min_ms']:.1f}",
            f"{s['median_ms']:.1f}",
            f"{s['p95_ms']:.1f}",
            f"{s['max_ms']:.1f}",
            f"{s['mean_ms']:.1f}",
            f"{s['stddev_ms']:.1f}",
            str(len(r["samples_ms"])),
        ])
    widths = [max(len(row[i]) for row in table) for i in range(len(header))]
    out_lines = [f"falsify bench  (runs={runs}, warmup={warmup})"]
    # Prepend a 2-space margin on every body row so that `row.index("  ")`
    # finds the same position (0) on every line regardless of how much
    # ljust padding the first column has. Without this leading margin,
    # shorter commands pad with enough trailing spaces to create a "  "
    # run inside col 0, breaking downstream alignment checks.
    for row in table:
        parts = [row[0].ljust(widths[0])]
        for j in range(1, len(header)):
            parts.append(row[j].rjust(widths[j]))
        out_lines.append("  " + "  ".join(parts))
    return "\n".join(out_lines) + "\n"


def cmd_linkage(args: argparse.Namespace) -> int:
    """prml-linkage/0 (draft): start / finish / verify execution-linkage records.

    Records are written in canonical form, so the SHA-256 of the file's bytes
    IS the record hash — committable to the registry as-is for tier L3.
    """
    import falsify_linkage as fl

    def _load_yaml(path_str: str, what: str):
        p = Path(path_str)
        if not p.exists():
            print(f"falsify linkage: {what} not found: {p}", file=sys.stderr)
            return None
        try:
            data = yaml.safe_load(p.read_text())
        except yaml.YAMLError as e:
            print(f"falsify linkage: cannot parse {p}: {e}", file=sys.stderr)
            return None
        if not isinstance(data, dict):
            print(f"falsify linkage: {p} must be a YAML mapping", file=sys.stderr)
            return None
        return data

    def _write_record(record: dict, out_path: str, label: str) -> None:
        canonical = fl.canonicalize(record)
        Path(out_path).write_text(canonical)
        print(f"{label}: {out_path}")
        print(f"  record hash: {fl.linkage_hash(record)}")
        print(f"  tier L3: POST the file to https://registry.falsify.dev/commit before the run completes")

    if args.linkage_cmd == "start":
        manifest = _load_yaml(args.manifest, "manifest")
        if manifest is None:
            return EXIT_BAD_SPEC
        dataset_hash = (manifest.get("dataset") or {}).get("hash")
        if not isinstance(dataset_hash, str):
            print("falsify linkage: manifest has no dataset.hash", file=sys.stderr)
            return EXIT_BAD_SPEC
        _, manifest_hash = _canonical_and_hash(manifest)
        model = manifest.get("model") or {}
        try:
            record = fl.build_start(
                manifest_hash=manifest_hash,
                run_id=args.run_id,
                environment=args.environment,
                dataset_hash=dataset_hash,
                receipt=args.receipt,
                model_version=model.get("id") if isinstance(model, dict) else None,
            )
        except ValueError as e:
            print(f"falsify linkage: {e}", file=sys.stderr)
            return EXIT_BAD_SPEC
        _write_record(record, args.out, "start record")
        return EXIT_PASS

    if args.linkage_cmd == "finish":
        start = _load_yaml(args.start, "start record")
        if start is None:
            return EXIT_BAD_SPEC
        if args.result_file:
            data = Path(args.result_file).read_bytes()
            digest = hashlib.sha256(data).hexdigest()
        elif args.digest:
            digest = args.digest
        else:
            print("falsify linkage finish: provide --result-file or --digest", file=sys.stderr)
            return EXIT_BAD_SPEC
        exit_code = args.exit_code
        if exit_code is None:
            if not args.manifest:
                print("falsify linkage finish: provide --exit-code, or --manifest to compute the verdict", file=sys.stderr)
                return EXIT_BAD_SPEC
            manifest = _load_yaml(args.manifest, "manifest")
            if manifest is None:
                return EXIT_BAD_SPEC
            comparator, threshold = manifest.get("comparator"), manifest.get("threshold")
            ok = fl._COMPARATORS.get(comparator, lambda a, b: None)(args.observed, threshold) \
                if isinstance(threshold, (int, float)) else None
            if ok is None:
                print("falsify linkage finish: manifest comparator/threshold unusable for verdict", file=sys.stderr)
                return EXIT_BAD_SPEC
            exit_code = EXIT_PASS if ok else EXIT_FAIL
        try:
            record = fl.finalize(start, args.observed, digest, exit_code)
        except ValueError as e:
            print(f"falsify linkage: {e}", file=sys.stderr)
            return EXIT_BAD_SPEC
        _write_record(record, args.out, "final record")
        print(f"  verdict exit_code: {exit_code}")
        return EXIT_PASS

    # verify
    final = _load_yaml(args.final, "final record")
    if final is None:
        return EXIT_BAD_SPEC
    start = _load_yaml(args.start, "start record") if args.start else None
    if args.start and start is None:
        return EXIT_BAD_SPEC
    manifest = _load_yaml(args.manifest, "manifest") if args.manifest else None
    if args.manifest and manifest is None:
        return EXIT_BAD_SPEC
    report = fl.verify(final, start_record=start, manifest=manifest)
    tier = report["tier"] or "-"
    print(f"linkage verify: {'OK' if report['ok'] else 'FAILED'} (tier {tier})")
    for f in report["failures"]:
        print(f"  ✗ {f['check']}: {f['detail']}")
    for s in report["skipped"]:
        print(f"  – skipped: {s}")
    return EXIT_PASS if report["ok"] else EXIT_FAIL


def _conform_load_vectors(path: Path) -> list[dict]:
    """Load conformance vectors from either format.

    JSON file  → the v0.1 test-vectors.json array.
    Directory  → RFC v0.2 P-04 layout: <id>/manifest.yaml + <id>/expected_hash.txt.
    """
    if path.is_file():
        vectors = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(vectors, list):
            raise ValueError(f"{path} is not a JSON array of vectors")
        return vectors
    if not path.is_dir():
        raise ValueError(f"vectors path does not exist: {path}")
    vectors = []
    for d in sorted(p for p in path.iterdir() if p.is_dir()):
        manifest_path = d / "manifest.yaml"
        hash_path = d / "expected_hash.txt"
        if not (manifest_path.exists() and hash_path.exists()):
            continue
        canonical = manifest_path.read_text(encoding="utf-8")
        vectors.append(
            {
                "id": d.name,
                "title": d.name,
                "input": yaml.safe_load(canonical),
                "canonical": canonical,
                "hash": hash_path.read_text(encoding="utf-8").strip(),
            }
        )
    if not vectors:
        raise ValueError(f"no vector directories found under {path}")
    return vectors


def cmd_conform(args: argparse.Namespace) -> int:
    """Run the conformance vectors against a target implementation (RFC v0.2 P-04).

    Target protocol (same as spec/test-vectors/v0.1/conform.py): the target is
    spawned per vector, receives the vector input as JSON on stdin, and must
    print {"canonical": "...", "hash": "..."} on stdout.
    """
    import shlex
    import subprocess

    vectors_path = Path(args.vectors) if args.vectors else (
        Path(__file__).parent / "spec" / "test-vectors" / "v0.1" / "vectors"
    )
    if not vectors_path.exists():
        # fall back to the JSON file when the directory export is absent
        fallback = Path(__file__).parent / "spec" / "test-vectors" / "v0.1" / "test-vectors.json"
        if fallback.exists():
            vectors_path = fallback
        else:
            print(f"falsify conform: vectors not found at {vectors_path}", file=sys.stderr)
            return EXIT_BAD_SPEC
    try:
        vectors = _conform_load_vectors(vectors_path)
    except ValueError as exc:
        print(f"falsify conform: {exc}", file=sys.stderr)
        return EXIT_BAD_SPEC

    argv = shlex.split(args.target)
    passed = 0
    failures: list[tuple[str, str]] = []
    for v in vectors:
        try:
            proc = subprocess.run(
                argv,
                input=json.dumps(v["input"]),
                capture_output=True,
                text=True,
                timeout=30,
            )
            if proc.returncode != 0:
                raise RuntimeError(f"target exit {proc.returncode}: {proc.stderr.strip()[:200]}")
            out = json.loads(proc.stdout)
            if out.get("canonical") != v["canonical"]:
                raise RuntimeError("canonical bytes differ")
            if out.get("hash") != v["hash"]:
                raise RuntimeError(f"hash differs (expected {v['hash'][:12]}…, got {str(out.get('hash'))[:12]}…)")
        except Exception as exc:  # noqa: BLE001
            failures.append((v["id"], str(exc)))
            print(f"  FAIL  {v['id']}  {v.get('title', '')}")
            continue
        passed += 1
        print(f"  ok    {v['id']}  {v.get('title', '')}")

    print(f"\n{passed}/{len(vectors)} vectors passed")
    for vid, why in failures:
        print(f"  {vid}: {why}")
    return EXIT_PASS if not failures else EXIT_FAIL


def cmd_bench(args: argparse.Namespace) -> int:
    runs = max(1, min(int(args.runs), _BENCH_MAX_RUNS))
    warmup = max(0, int(args.warmup))
    commands = _bench_parse_commands(args.commands)
    if not commands:
        print(
            "falsify bench: --commands list is empty",
            file=sys.stderr,
        )
        return EXIT_BAD_SPEC

    script_path = str(Path(__file__).resolve())
    results: list[dict] = []
    # bench is a LATENCY probe, not a correctness check. A semantic
    # nonzero exit (e.g. `score` returning EXIT_FAIL=10 on an empty
    # repo, or `verdict` returning 10 on a FAIL claim) is still a
    # legitimate timing sample. We only treat a command as "broken"
    # when argparse itself rejects it as unknown — detectable via
    # the first iteration's stderr signature.
    _ARGPARSE_REJECT_MARKERS = ("invalid choice", "unrecognized arguments")
    any_argparse_reject = False

    for cmd_str in commands:
        cmd_argv = cmd_str.split()
        samples_ms: list[float] = []
        first_stderr = ""
        first_rc = 0

        for _ in range(warmup):
            with tempfile.TemporaryDirectory() as tmp:
                r = subprocess.run(
                    [sys.executable, script_path, *cmd_argv],
                    cwd=tmp, capture_output=True, text=True,
                )
            # warmup nonzero is tolerated for the same reason below

        for iteration in range(runs):
            with tempfile.TemporaryDirectory() as tmp:
                start = time.perf_counter()
                r = subprocess.run(
                    [sys.executable, script_path, *cmd_argv],
                    cwd=tmp, capture_output=True, text=True,
                )
                elapsed_ms = (time.perf_counter() - start) * 1000.0
            if iteration == 0:
                first_stderr = r.stderr
                first_rc = r.returncode
            samples_ms.append(elapsed_ms)

        # Argparse-reject detection: propagate the subprocess stderr
        # (which names the bad command) and flag overall failure.
        if first_rc != 0 and any(
            marker in first_stderr for marker in _ARGPARSE_REJECT_MARKERS
        ):
            sys.stderr.write(first_stderr)
            any_argparse_reject = True

        results.append({
            "command": cmd_str,
            "samples_ms": [round(x, 4) for x in samples_ms],
            "stats": _bench_stats(samples_ms),
        })

    if args.json:
        payload = {
            "runs": runs,
            "warmup": warmup,
            "commands": results,
            "system": {
                "python": platform.python_version(),
                "platform": sys.platform,
            },
        }
        print(json.dumps(payload, indent=2))
    else:
        sys.stdout.write(_bench_format_table(results, runs, warmup))
    return EXIT_BAD_SPEC if any_argparse_reject else EXIT_PASS


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="falsify",
        description="Pre-registration + CI for AI-agent claims.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"falsify {__version__}",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_version = sub.add_parser("version", help="Print the version")
    p_version.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable JSON: {name, version}",
    )
    p_version.set_defaults(func=cmd_version)

    p_init = sub.add_parser("init", help="Scaffold a new claim spec")
    p_init.add_argument(
        "name",
        nargs="?",
        help="Claim name (used as directory under .falsify/). "
             "Required unless --template is given.",
    )
    p_init.add_argument(
        "--name",
        dest="claim_name",
        help="Override claim name when using --template "
             "(default: template name).",
    )
    p_init.add_argument(
        "--template",
        help=(
            "Scaffold a complete working claim from a template. "
            "Available: " + ", ".join(sorted(_INIT_TEMPLATES))
        ),
    )
    p_init.add_argument(
        "--dir",
        help="Target directory for template files "
             "(default: claims/<name>/).",
    )
    p_init.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing files / directories",
    )
    p_init.set_defaults(func=cmd_init)

    p_lock = sub.add_parser("lock", help="Hash and freeze a claim (pre-register)")
    p_lock.add_argument("name", help="Claim name")
    p_lock.add_argument(
        "--force",
        action="store_true",
        help="Relock even if the spec hash has changed since last lock",
    )
    p_lock.set_defaults(func=cmd_lock)

    p_run = sub.add_parser("run", help="Evaluate a locked claim against current state")
    p_run.add_argument("name", help="Claim name")
    p_run.set_defaults(func=cmd_run)

    p_diff = sub.add_parser(
        "diff",
        help="Unified diff between a locked spec's canonical YAML and the current spec.yaml",
    )
    p_diff.add_argument(
        "name",
        nargs="?",
        help="Claim name (required unless --file-vs-file is given)",
    )
    p_diff_modes = p_diff.add_mutually_exclusive_group()
    p_diff_modes.add_argument(
        "--lock-vs-file",
        action="store_true",
        help="Compare the claim's locked canonical YAML against its current spec.yaml (default)",
    )
    p_diff_modes.add_argument(
        "--file-vs-file",
        nargs=2,
        metavar=("A", "B"),
        help="Canonical diff between two arbitrary YAML files",
    )
    p_diff.set_defaults(func=cmd_diff)

    p_replay = sub.add_parser(
        "replay",
        help="Re-run a stored run's metric and assert the value matches",
    )
    p_replay.add_argument(
        "run_id",
        help="Run identifier (the timestamp directory under .falsify/<claim>/runs/)",
    )
    p_replay.add_argument(
        "--claim",
        help="Disambiguate when the same run_id appears under multiple claims",
    )
    p_replay.add_argument(
        "--tolerance",
        type=float,
        default=0.0,
        help="Absolute tolerance for float comparison (default 0.0 = exact match)",
    )
    p_replay.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable JSON",
    )
    p_replay.set_defaults(func=cmd_replay)

    p_verdict = sub.add_parser("verdict", help="Report PASS/FAIL for a claim")
    p_verdict.add_argument("name", help="Claim name")
    p_verdict.set_defaults(func=cmd_verdict)

    p_guard = sub.add_parser(
        "guard",
        help="CI wrapper — text-match, scan, or wrap modes",
        description=(
            "Three modes:\n"
            "  falsify guard              scan for FAIL/STALE claims (exit 10 on hit)\n"
            "  falsify guard \"text\"       block affirmative claims vs logged FAIL/INCONCLUSIVE (exit 11)\n"
            "  falsify guard -- <cmd>    run <cmd>; on success, also scan"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p_guard.add_argument(
        "rest",
        nargs=argparse.REMAINDER,
        help="Claim text, or `-- cmd args...` for wrap mode",
    )
    p_guard.set_defaults(func=cmd_guard)

    p_verify = sub.add_parser(
        "verify",
        help="Audit a JSONL export for chain integrity and ordering",
    )
    p_verify.add_argument(
        "jsonl_path",
        help="Path to the JSONL file produced by `falsify export`",
    )
    p_verify.add_argument(
        "--strict",
        action="store_true",
        help="Treat WARN findings as FAIL (exit 10)",
    )
    p_verify.add_argument(
        "--json",
        action="store_true",
        help="Emit a machine-readable JSON report",
    )
    p_verify.set_defaults(func=cmd_verify)

    p_trend = sub.add_parser(
        "trend",
        help="ASCII sparkline of a claim's metric across its recorded runs",
    )
    p_trend.add_argument("claim_name", help="Claim name")
    p_trend.add_argument(
        "--last",
        type=int,
        default=20,
        help="Number of most-recent runs to render (default 20, max 200)",
    )
    p_trend.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable JSON instead of text",
    )
    p_trend.add_argument(
        "--width",
        type=int,
        default=40,
        help="Sparkline width in columns (default 40)",
    )
    p_trend.add_argument(
        "--ascii",
        action="store_true",
        help="Use 5-level ASCII characters (_.oO#) instead of Unicode blocks",
    )
    p_trend.set_defaults(func=cmd_trend)

    p_why = sub.add_parser(
        "why",
        help="Explain a claim's current state and the next honest action",
    )
    p_why.add_argument("claim_name", help="Claim name")
    p_why.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable JSON",
    )
    p_why.add_argument(
        "--verbose",
        action="store_true",
        help="Include full hashes, exact timestamps, and recent runs",
    )
    p_why.set_defaults(func=cmd_why)

    p_score = sub.add_parser(
        "score",
        help="Aggregate single-number honesty score with multiple output formats",
    )
    p_score.add_argument(
        "--format",
        choices=["text", "json", "shields", "svg"],
        default="text",
        help="Output format (default text)",
    )
    p_score.add_argument(
        "--output",
        help="Write to PATH instead of stdout",
    )
    p_score.add_argument(
        "--threshold",
        type=float,
        default=0.8,
        help="Score threshold for 'ok' status (default 0.8)",
    )
    p_score.add_argument(
        "--strict",
        action="store_true",
        help="Treat 'warn' status as failure (exit 10)",
    )
    p_score.add_argument(
        "--scope",
        default="dogfood",
        help=(
            "Filter claims by spec 'kind' (default 'dogfood'). "
            "Use 'all' to score every locked claim, or any other kind "
            "string (e.g. 'case_study') to score only that kind."
        ),
    )
    p_score.set_defaults(func=cmd_score)

    p_export = sub.add_parser(
        "export",
        help="Write the verdict history as JSONL (audit trail, read-only)",
    )
    p_export.add_argument(
        "--output", help="Write to PATH instead of stdout",
    )
    p_export.add_argument(
        "--name", help="Filter by claim-name substring",
    )
    p_export.add_argument(
        "--since",
        help="Emit only records with ts >= this ISO 8601 date",
    )
    p_export.add_argument(
        "--include-runs",
        action="store_true",
        help="Include run records with stdout SHA-256 and a 200-char sample",
    )
    p_export.set_defaults(func=cmd_export)

    p_doctor = sub.add_parser(
        "doctor",
        help="Self-diagnostic: environment + repo + per-spec checks",
    )
    p_doctor.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable JSON",
    )
    p_doctor.add_argument(
        "--specs-only",
        action="store_true",
        help="Run only per-spec checks (skip environment and CI checks)",
    )
    p_doctor.set_defaults(func=cmd_doctor)

    p_hook = sub.add_parser(
        "hook",
        help="Install or uninstall the commit-msg guard hook",
    )
    hook_sub = p_hook.add_subparsers(dest="action", required=True)
    p_hook_install = hook_sub.add_parser(
        "install",
        help="Copy hooks/commit-msg into .git/hooks/, backing up any existing hook",
    )
    p_hook_install.add_argument(
        "--force",
        action="store_true",
        help="Reserved for install — currently unused, accepted for symmetry",
    )
    p_hook_install.set_defaults(func=cmd_hook)

    p_hook_uninstall = hook_sub.add_parser(
        "uninstall",
        help="Remove the installed commit-msg hook (restore .bak with --force)",
    )
    p_hook_uninstall.add_argument(
        "--force",
        action="store_true",
        help="Restore the most recent .bak backup without prompting",
    )
    p_hook_uninstall.set_defaults(func=cmd_hook)

    p_list = sub.add_parser("list", help="List all claims with their status")
    p_list.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable JSON instead of a table",
    )
    p_list.set_defaults(func=cmd_list)

    p_stats = sub.add_parser(
        "stats",
        help="Aggregate dashboard across all locked verdicts (informational)",
    )
    stats_mode = p_stats.add_mutually_exclusive_group()
    stats_mode.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable JSON",
    )
    stats_mode.add_argument(
        "--html",
        action="store_true",
        help="Emit a self-contained HTML dashboard (inline CSS, zero deps)",
    )
    p_stats.add_argument(
        "--output",
        help="Write output to PATH instead of stdout",
    )
    p_stats.add_argument(
        "--name",
        help="Filter to claim names containing this substring",
    )
    p_stats.set_defaults(func=cmd_stats)

    p_bench = sub.add_parser(
        "bench",
        help="Micro-benchmark CLI command latency",
    )
    p_bench.add_argument(
        "--runs", type=int, default=5,
        help="Number of timed runs per command (default: 5, capped at 100)",
    )
    p_bench.add_argument(
        "--warmup", type=int, default=1,
        help="Number of untimed warmup runs per command before the timed "
             "runs start (default: 1)",
    )
    p_bench.add_argument(
        "--commands", default=None,
        help="Comma-separated list of subcommands to bench "
             "(default: --help,--version,list,stats,score)",
    )
    p_bench.add_argument(
        "--json", action="store_true",
        help="Emit machine-readable JSON output",
    )
    p_bench.set_defaults(func=cmd_bench)

    p_conform = sub.add_parser(
        "conform",
        help="Run the PRML conformance vectors against a target implementation (RFC v0.2 P-04)",
    )
    p_conform.add_argument(
        "target",
        help="Target command, quoted if it has arguments "
             "(e.g. 'node impl/js/conform.js' or 'go run ./impl/go/cmd/conform')",
    )
    p_conform.add_argument(
        "--vectors", default=None,
        help="Path to a vectors directory (P-04 layout) or a test-vectors.json file "
             "(default: spec/test-vectors/v0.1/vectors)",
    )
    p_conform.set_defaults(func=cmd_conform)

    p_linkage = sub.add_parser(
        "linkage",
        help="prml-linkage/0 (draft): evidence the lock → run → result order",
    )
    linkage_sub = p_linkage.add_subparsers(dest="linkage_cmd", required=True)

    p_lk_start = linkage_sub.add_parser("start", help="Create a run-start record from a locked manifest")
    p_lk_start.add_argument("manifest", help="Path to the locked PRML manifest (YAML)")
    p_lk_start.add_argument("--run-id", required=True, help="Runner-native run identifier")
    p_lk_start.add_argument("--environment", required=True, help="Free-form runner fingerprint (os/framework/accelerator)")
    p_lk_start.add_argument("--receipt", default=None, help="Registry receipt URL for the manifest, if committed")
    p_lk_start.add_argument("-o", "--out", default="linkage-start.yaml", help="Output path (default: linkage-start.yaml)")
    p_lk_start.set_defaults(func=cmd_linkage)

    p_lk_finish = linkage_sub.add_parser("finish", help="Create the final record from a start record + result")
    p_lk_finish.add_argument("start", help="Path to the start record (YAML)")
    p_lk_finish.add_argument("--observed", type=float, required=True, help="Observed metric value")
    p_lk_finish.add_argument("--result-file", default=None, help="Raw result artifact; its SHA-256 becomes result.digest")
    p_lk_finish.add_argument("--digest", default=None, help="Precomputed SHA-256 of the result artifact (64 hex)")
    p_lk_finish.add_argument("--exit-code", type=int, default=None, choices=[0, 3, 10, 11], help="Verdict exit code; omit with --manifest to compute")
    p_lk_finish.add_argument("--manifest", default=None, help="Manifest to compute the verdict from (when --exit-code omitted)")
    p_lk_finish.add_argument("-o", "--out", default="linkage-final.yaml", help="Output path (default: linkage-final.yaml)")
    p_lk_finish.set_defaults(func=cmd_linkage)

    p_lk_verify = linkage_sub.add_parser("verify", help="Verify a final record (chain, chronology, verdict)")
    p_lk_verify.add_argument("final", help="Path to the final record (YAML)")
    p_lk_verify.add_argument("--start", default=None, help="Start record for tier L2 chain verification")
    p_lk_verify.add_argument("--manifest", default=None, help="Manifest for dataset + verdict checks")
    p_lk_verify.set_defaults(func=cmd_linkage)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
