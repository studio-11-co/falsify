#!/usr/bin/env python3
"""Opik <-> PRML bridge — lock the eval bar before the metrics run.

Opik's `aggregated_scores` tell you what a run produced. What no run record can
say about itself is what the bar WAS before the run — which metric decides the
claim, what mean counts as success, which items (by content, not by name) the
claim is about. All of those are chosen by the party publishing the number, and
each can be adjusted after the mean is known.

THE HONEST DESIGN (same split as our Inspect / hud / Mastra / Laminar /
promptfoo bridges):
    lock   — BEFORE the run: a PRML manifest binds the metric name (= the
             aggregated_scores key), the comparator and threshold, a SHA-256
             over the canonical JSON of the items, and the seed. Locked to a
             digest before any output exists.
    run    — Opik's own `evaluate_on_dict_items`, end to end: Opik's public,
             platform-free evaluation entry point ("useful for optimization
             scenarios ... without requiring a Dataset object or creating an
             experiment", their docstring). Real task execution, real
             `Equals` metric, real `aggregate_evaluation_scores()`.
    verify — AFTER: aggregated mean vs the pre-locked bar.
             Exit 0 PASS / 10 FAIL / 3 TAMPERED.

Everything scored here is real Opik machinery — the evaluator, the metric, the
aggregation are all imported, not imitated. One honest note on tracing: the
evaluation engine still creates trace records ("It creates traces for tracking",
their docstring), and without an API key the background uploads are rejected
with a 401 and dropped — harmless, nothing blocks, and no data leaves
successfully. The scores are computed locally either way; the lock/verify split
is unchanged when tracking is fully configured, because the manifest never
depends on where scores are displayed.

Run:  OPIK_TRACK_DISABLE=true python3 opik_prml.py
Needs: pip install opik falsify
"""

from __future__ import annotations

import hashlib
import json
import os

os.environ.setdefault("OPIK_TRACK_DISABLE", "true")

import opik
from opik.evaluation import evaluate_on_dict_items
from opik.evaluation.metrics import Equals

from falsify_prml import evaluate_predicate, manifest_hash, validate_manifest

EXIT_PASS, EXIT_TAMPERED, EXIT_FAIL = 0, 3, 10


# ── the eval under test ──────────────────────────────────────────────────────
# Judge-free on purpose: Equals has no model in the loop, so the demo is
# deterministic and the only thing under discussion is the bar.

ITEMS = [
    {"question": "capital of France", "expected_output": "Paris"},
    {"question": "2 + 2", "expected_output": "4"},
    {"question": "capital of Estonia", "expected_output": "Tallinn"},
    {"question": "first prime", "expected_output": "2"},
]

ANSWERS = {  # stands in for the model; swap in a real task freely
    "capital of France": "Paris",
    "2 + 2": "4",
    "capital of Estonia": "Tallinn",
    "first prime": "1",  # wrong on purpose: 3/4 = 0.75
}


def task(item: dict) -> dict:
    return {"output": ANSWERS[item["question"]]}


# ── lock: seal the bar before anything runs ──────────────────────────────────

def items_hash(items: list[dict]) -> str:
    """SHA-256 over canonical JSON of the items — sorted keys, compact — so
    'same dataset' is a byte-level claim, not a filename."""
    canon = json.dumps(items, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canon.encode()).hexdigest()


def build_manifest(items: list[dict]) -> dict:
    return {
        "version": "prml/0.1",
        "claim_id": "01991bd0-6a3b-7c1e-8f2d-4b5c6d7e8f90",
        "created_at": "2026-08-19T12:00:00Z",
        "metric": "equals_metric",   # Opik's name for Equals = aggregated_scores key
        "comparator": ">=",
        "threshold": 0.7,
        "dataset": {"id": "opik-demo-qa-v1", "hash": items_hash(items)},
        "seed": 42,
        "producer": {"id": "examples/opik"},
    }


# ── run: Opik itself, for real ───────────────────────────────────────────────

def run_eval(items: list[dict]) -> float:
    # Quieten what we can: Opik's public runtime toggle for @track-decorated
    # code. The evaluation engine itself still creates its eval traces; see the
    # module docstring for what happens to them without credentials.
    opik.set_tracing_active(False)
    result = evaluate_on_dict_items(
        items=items,
        task=task,
        scoring_metrics=[Equals(case_sensitive=True, track=False)],
        scoring_key_mapping={"reference": "expected_output"},
        verbose=0,
    )
    stats = result.aggregate_evaluation_scores()
    return stats["equals_metric"].mean


# ── verify: the locked bar decides ───────────────────────────────────────────

def verify(manifest: dict, locked: str, observed: float) -> int:
    errors = validate_manifest(manifest)
    if errors or manifest_hash(manifest) != locked:
        print("verdict: TAMPERED — manifest does not match the pre-run lock")
        return EXIT_TAMPERED
    ok = evaluate_predicate(observed, manifest["comparator"], manifest["threshold"])
    print(f"observed {manifest['metric']} mean = {observed}  "
          f"vs locked bar {manifest['comparator']} {manifest['threshold']}")
    print(f"verdict: {'PASS' if ok else 'FAIL'}")
    return EXIT_PASS if ok else EXIT_FAIL


def main() -> int:
    # 1. lock — before any output exists
    manifest = build_manifest(ITEMS)
    errors = validate_manifest(manifest)
    assert not errors, errors
    locked = manifest_hash(manifest)
    print(f"locked bar: equals_metric >= 0.7, items {manifest['dataset']['hash'][:16]}…")
    print(f"manifest sha256: {locked}\n")

    # 2. run — Opik's own platform-free evaluator, real metric, real aggregation
    observed = run_eval(ITEMS)

    # 3. verify against the pre-locked bar
    rc = verify(manifest, locked, observed)

    # 4. adversarial: lower the bar after seeing the mean
    print("\n-- adversarial: threshold edited 0.7 -> 0.5 AFTER the run --")
    doctored = dict(manifest, threshold=0.5)
    rc2 = verify(doctored, locked, observed)
    assert rc2 == EXIT_TAMPERED, "tamper demo must be caught"
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
