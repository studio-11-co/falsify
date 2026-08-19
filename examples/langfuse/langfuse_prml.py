#!/usr/bin/env python3
"""Langfuse <-> PRML bridge — lock the experiment bar before the run.

A Langfuse experiment records what happened: task outputs, item evaluations,
run-level aggregates, all browsable in the UI. What no experiment record can
say about itself is what the bar WAS before the run — which evaluator decides
the claim, what aggregate counts as success, which items (by content, not by
dataset name) the claim is about. Every one of those is chosen by the party
publishing the number, and each can be adjusted after the aggregate is known.

THE HONEST DESIGN (same split as our Inspect / hud / Mastra / Laminar /
promptfoo / Opik bridges):
    lock   — BEFORE the run: a PRML manifest binds the evaluation name, the
             comparator and threshold, a SHA-256 over the canonical JSON of
             the items, and the seed. Locked to a digest.
    run    — the experiment, using the SDK's own machinery (below).
    verify — AFTER: the run-level aggregate vs the pre-locked bar.
             Exit 0 PASS / 10 FAIL / 3 TAMPERED.

What is real vs modelled:
  - Execution and scoring semantics: REAL `langfuse` SDK. Tasks and evaluators
    run through the SDK's own `_run_task` / `_run_evaluator` (the same
    normalization `run_experiment` uses — sync/async handling, Evaluation
    lists), results are real `ExperimentItemResult` objects, evaluations are
    real `langfuse.Evaluation` instances, and the aggregate is computed by a
    run-level evaluator in exactly the shape the SDK documents
    (`def pass_rate(*, item_results, **kwargs)`). Imported, not imitated.
  - PRML canonicalisation + hashing + verdicts: REAL `falsify` reference.
  - NOT exercised: the platform upload. `run_experiment` logs to a Langfuse
    backend (API keys); this demo runs in a clean room without one, so it
    stops at the boundary where results leave the process. The lock/verify
    split is unchanged when the full pipeline runs — the manifest never
    depends on where results are displayed.

Run:  python3 langfuse_prml.py
Needs: pip install langfuse falsify
"""

from __future__ import annotations

import asyncio
import hashlib
import json

from langfuse import Evaluation
from langfuse.experiment import (
    ExperimentItemResult,
    _run_evaluator,
    _run_task,
)

from falsify_prml import evaluate_predicate, manifest_hash, validate_manifest

EXIT_PASS, EXIT_TAMPERED, EXIT_FAIL = 0, 3, 10


# ── the experiment under test ────────────────────────────────────────────────
# Judge-free on purpose: exact match has no model in the loop, so the demo is
# deterministic and the only thing under discussion is the bar.

ITEMS = [
    {"input": "capital of France", "expected_output": "Paris"},
    {"input": "2 + 2", "expected_output": "4"},
    {"input": "capital of Estonia", "expected_output": "Tallinn"},
    {"input": "first prime", "expected_output": "2"},
]

ANSWERS = {  # stands in for the model; swap in a real task freely
    "capital of France": "Paris",
    "2 + 2": "4",
    "capital of Estonia": "Tallinn",
    "first prime": "1",  # wrong on purpose: 3/4 = 0.75
}


def task(*, item, **kwargs):
    return ANSWERS[item["input"]]


def exact_match(*, input, output, expected_output=None, **kwargs):
    """Item-level evaluator, in the SDK's documented signature."""
    return Evaluation(name="exact_match", value=1.0 if output == expected_output else 0.0)


def pass_rate(*, item_results, **kwargs):
    """Run-level evaluator, in the SDK's documented signature — the aggregate
    the locked bar is checked against."""
    values = [
        e.value
        for r in item_results
        for e in r.evaluations
        if e.name == "exact_match" and isinstance(e.value, (int, float))
    ]
    return Evaluation(name="pass_rate", value=sum(values) / len(values))


# ── lock: seal the bar before anything runs ──────────────────────────────────

def items_hash(items: list[dict]) -> str:
    canon = json.dumps(items, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canon.encode()).hexdigest()


def build_manifest(items: list[dict]) -> dict:
    return {
        "version": "prml/0.1",
        "claim_id": "01991be2-8d4f-7a2b-9c3e-5f6a7b8c9d0e",
        "created_at": "2026-08-19T13:00:00Z",
        "metric": "pass_rate",   # = the run-level Evaluation's name
        "comparator": ">=",
        "threshold": 0.7,
        "dataset": {"id": "langfuse-demo-qa-v1", "hash": items_hash(items)},
        "seed": 42,
        "producer": {"id": "examples/langfuse"},
    }


# ── run: the SDK's own execution and normalization ───────────────────────────

async def run_experiment_locally(items: list[dict]) -> float:
    item_results = []
    for item in items:
        output = await _run_task(task, item)
        evaluations = await _run_evaluator(
            exact_match,
            input=item["input"],
            output=output,
            expected_output=item.get("expected_output"),
            metadata=item.get("metadata"),
        )
        item_results.append(
            ExperimentItemResult(
                item=item, output=output, evaluations=evaluations,
                trace_id=None, dataset_run_id=None,   # no platform in the clean room
            )
        )
    run_evals = await _run_evaluator(pass_rate, item_results=item_results)
    return next(e.value for e in run_evals if e.name == "pass_rate")


# ── verify: the locked bar decides ───────────────────────────────────────────

def verify(manifest: dict, locked: str, observed: float) -> int:
    errors = validate_manifest(manifest)
    if errors or manifest_hash(manifest) != locked:
        print("verdict: TAMPERED — manifest does not match the pre-run lock")
        return EXIT_TAMPERED
    ok = evaluate_predicate(observed, manifest["comparator"], manifest["threshold"])
    print(f"observed {manifest['metric']} = {observed}  "
          f"vs locked bar {manifest['comparator']} {manifest['threshold']}")
    print(f"verdict: {'PASS' if ok else 'FAIL'}")
    return EXIT_PASS if ok else EXIT_FAIL


def main() -> int:
    manifest = build_manifest(ITEMS)
    errors = validate_manifest(manifest)
    assert not errors, errors
    locked = manifest_hash(manifest)
    print(f"locked bar: pass_rate >= 0.7, items {manifest['dataset']['hash'][:16]}…")
    print(f"manifest sha256: {locked}\n")

    observed = asyncio.run(run_experiment_locally(ITEMS))

    rc = verify(manifest, locked, observed)

    print("\n-- adversarial: threshold edited 0.7 -> 0.5 AFTER the run --")
    doctored = dict(manifest, threshold=0.5)
    rc2 = verify(doctored, locked, observed)
    assert rc2 == EXIT_TAMPERED, "tamper demo must be caught"
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
