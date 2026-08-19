#!/usr/bin/env python3
"""Laminar <-> PRML bridge — lock the eval bar before `evaluate()` runs.

Laminar's `evaluate()` is honest about what it records: executor outputs,
evaluator scores, `average_scores` at the end. What nothing in that record can
say is what the bar WAS before the run — which evaluator decides the claim,
what threshold counts as success, which dataset the claim is about. All of
those are chosen by the party publishing the number, and every one of them can
be adjusted after `average_scores` is known. A dashboard shows you the score;
it cannot show you that the pass bar predates the score.

THE HONEST DESIGN (same split as our Inspect / hud / Mastra bridges):
    lock   — BEFORE the run: build a PRML manifest binding the evaluator name
             (the metric), the comparator and threshold, a SHA-256 over the
             canonical JSON of the dataset, and the seed. Lock it to a digest.
    run    — the eval, using the SDK's own semantics (below).
    verify — AFTER: read `average_scores[metric]`, check it against the
             pre-locked manifest. Exit 0 PASS / 10 FAIL / 3 TAMPERED.

What is real vs modelled:
  - Scoring semantics: REAL `lmnr` SDK — evaluators are invoked exactly as
    `Evaluation._evaluate_datapoint` invokes them (`evaluator(output, target)`,
    a numeric return keyed by evaluator name, a dict merged as-is), results are
    real `EvaluationResultDatapoint` objects, and the aggregate comes from the
    SDK's own `get_average_scores` — the same function whose output the
    platform displays. Import it, don't imitate it.
  - PRML canonicalisation + hashing + verdicts: REAL `falsify_prml` reference.
  - NOT exercised: the platform upload. `evaluate()` requires a Laminar
    backend (API key or self-hosted stack); this demo runs in a clean room
    with neither, so it stops at the boundary where scores leave the process.
    The lock/verify split is exactly the same when the full `evaluate()`
    pipeline runs — the manifest never depends on where scores are displayed.

Run:  python3 laminar_prml.py           # lock -> run -> verify -> tamper demo
Needs: pip install lmnr falsify
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import sys
import uuid

from lmnr.sdk.evaluations import get_average_scores
from lmnr.sdk.types import Datapoint, EvaluationResultDatapoint

from falsify_prml import evaluate_predicate, manifest_hash, validate_manifest

EXIT_PASS, EXIT_TAMPERED, EXIT_FAIL = 0, 3, 10


# ── the eval under test ──────────────────────────────────────────────────────
# Judge-free on purpose: an exact-match evaluator has no model in the loop, so
# the demo is deterministic and the only thing under discussion is the bar.

TESTSET = [
    {"data": {"question": "capital of France"}, "target": "Paris"},
    {"data": {"question": "2 + 2"}, "target": "4"},
    {"data": {"question": "capital of Estonia"}, "target": "Tallinn"},
    {"data": {"question": "first prime"}, "target": "2"},
]

ANSWERS = {  # stands in for the model; swap in a real executor freely
    "capital of France": "Paris",
    "2 + 2": "4",
    "capital of Estonia": "Tallinn",
    "first prime": "1",  # wrong on purpose: 3/4 = 0.75
}


def executor(data: dict) -> str:
    return ANSWERS[data["question"]]


def exact_match(output: str, target: str) -> float:
    return 1.0 if output == target else 0.0


EVALUATORS = {"exact_match": exact_match}


# ── lock: seal the bar before anything runs ──────────────────────────────────

def dataset_hash(testset: list[dict]) -> str:
    """SHA-256 over the canonical JSON of the dataset — sorted keys, compact
    separators — so 'same dataset' is a byte-level claim, not a filename."""
    canon = json.dumps(testset, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canon.encode()).hexdigest()


def build_manifest(testset: list[dict]) -> dict:
    return {
        "version": "prml/0.1",
        "claim_id": "01991b4e-2f6a-7c8d-9e0f-1a2b3c4d5e6f",
        "created_at": "2026-08-19T08:00:00Z",
        "metric": "exact_match",       # = the evaluator name, = the average_scores key
        "comparator": ">=",
        "threshold": 0.7,
        "dataset": {"id": "laminar-demo-qa-v1", "hash": dataset_hash(testset)},
        "seed": 42,
        "producer": {"id": "examples/laminar"},
    }


# ── run: the SDK's own scoring semantics ─────────────────────────────────────

async def run_eval(testset: list[dict]) -> dict[str, float]:
    """Invoke evaluators the way lmnr's Evaluation._evaluate_datapoint does,
    build real EvaluationResultDatapoint objects, aggregate with the SDK's own
    get_average_scores. The platform upload is the only step not taken."""
    results: list[EvaluationResultDatapoint] = []
    for index, item in enumerate([Datapoint(**d) for d in testset]):
        output = executor(item.data)
        scores: dict[str, float] = {}
        for name, evaluator in EVALUATORS.items():
            value = evaluator(output, item.target)   # sync path of the SDK
            if isinstance(value, (int, float)):      # numeric -> keyed by name,
                scores[name] = value                 # dict -> merged: SDK rule
            else:
                scores.update(value)
        results.append(EvaluationResultDatapoint(
            id=uuid.uuid4(), index=index, data=item.data, target=item.target,
            executor_output=output, scores=scores,
            trace_id=uuid.uuid4(), executor_span_id=uuid.uuid4(),
        ))
    return get_average_scores(results)


# ── verify: the locked bar decides ───────────────────────────────────────────

def verify(manifest: dict, locked_hash: str, average_scores: dict) -> int:
    errors = validate_manifest(manifest)
    if errors or manifest_hash(manifest) != locked_hash:
        print("verdict: TAMPERED — manifest does not match the pre-run lock")
        return EXIT_TAMPERED
    observed = average_scores[manifest["metric"]]
    ok = evaluate_predicate(observed, manifest["comparator"],
                            manifest["threshold"])
    print(f"observed {manifest['metric']} = {observed}  "
          f"vs locked bar {manifest['comparator']} {manifest['threshold']}")
    print(f"verdict: {'PASS' if ok else 'FAIL'}")
    return EXIT_PASS if ok else EXIT_FAIL


def main() -> int:
    # 1. lock — before any output exists
    manifest = build_manifest(TESTSET)
    errors = validate_manifest(manifest)
    assert not errors, errors
    locked = manifest_hash(manifest)
    print(f"locked bar: exact_match >= 0.7, dataset {manifest['dataset']['hash'][:16]}…")
    print(f"manifest sha256: {locked}\n")

    # 2. run — SDK semantics, judge-free, deterministic
    average_scores = asyncio.run(run_eval(TESTSET))

    # 3. verify against the pre-locked bar
    rc = verify(manifest, locked, average_scores)

    # 4. adversarial: lower the bar after seeing the score
    print("\n-- adversarial: threshold edited 0.7 -> 0.5 AFTER the run --")
    doctored = dict(manifest, threshold=0.5)
    rc2 = verify(doctored, locked, average_scores)
    assert rc2 == EXIT_TAMPERED, "tamper demo must be caught"
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
