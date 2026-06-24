"""Runnable, offline DeepEval + PRML demo — no LLM, no API key, no network.

Two scenarios, both using DeepEval's real SDK (LLMTestCase, BaseMetric):

  A. Honest PASS  — lock accuracy >= 0.85, run, observe 0.90, verify -> PASS.
  B. Gamed run    — lock accuracy >= 0.95, run, observe 0.90 (a FAIL); then
                    quietly lower the locked threshold to 0.85 to make it green
                    -> PRML returns TAMPERED, not PASS.

Run:  python run_with_prml.py
"""
from __future__ import annotations

import json
import os
import sys

from deepeval.test_case import LLMTestCase

from exact_match_metric import ExactMatchMetric
from prml_deepeval import PrmlLock, lock_metric, verify_observed

HERE = os.path.dirname(os.path.abspath(__file__))
DATASET = os.path.join(HERE, "eval_set.jsonl")


def load_cases() -> list[LLMTestCase]:
    cases = []
    with open(DATASET, encoding="utf-8") as f:
        for line in f:
            row = json.loads(line)
            cases.append(
                LLMTestCase(
                    input=row["input"],
                    actual_output=row["actual_output"],
                    expected_output=row["expected_output"],
                )
            )
    return cases


def observed_accuracy(metric: ExactMatchMetric, cases: list[LLMTestCase]) -> float:
    """Aggregate the per-case DeepEval scores into a dataset-level accuracy."""
    scores = [metric.measure(c) for c in cases]
    return sum(scores) / len(scores)


def banner(title: str) -> None:
    print(f"\n{'=' * 64}\n{title}\n{'=' * 64}")


def main() -> int:
    cases = load_cases()

    # ----- Scenario A: honest claim that holds -------------------------------
    banner("A. Honest claim — accuracy >= 0.85")
    metric = ExactMatchMetric(threshold=0.85)
    lock = lock_metric(
        metric,
        claim_id="01900000-0000-7000-8000-0000deeeva10",
        metric_id="accuracy",
        created_at="2026-06-24T12:00:00Z",
        dataset_path=DATASET,
        dataset_id="qa-exactmatch-10",
        seed=42,
        producer_id="falsify.dev/examples/deepeval",
    )
    print(f"locked BEFORE run   sha256={lock.digest}")
    print(f"  bar: {lock.manifest['metric']} {lock.manifest['comparator']} "
          f"{lock.manifest['threshold']}   dataset={lock.manifest['dataset']['hash'][:16]}…")
    observed = observed_accuracy(metric, cases)
    print(f"ran DeepEval        observed accuracy = {observed:.4f}")
    verdict_a = verify_observed(lock, observed)
    print(f"verify -> {verdict_a}")

    # ----- Scenario B: the moved goalpost ------------------------------------
    banner("B. Gamed run — lock 0.95, miss, then lower the bar to 0.85")
    strict = ExactMatchMetric(threshold=0.95)
    lock_b = lock_metric(
        strict,
        claim_id="01900000-0000-7000-8000-0000deeeva20",
        metric_id="accuracy",
        created_at="2026-06-24T12:00:00Z",
        dataset_path=DATASET,
        dataset_id="qa-exactmatch-10",
        seed=42,
        producer_id="falsify.dev/examples/deepeval",
    )
    print(f"locked BEFORE run   sha256={lock_b.digest}")
    print(f"  bar: accuracy >= {lock_b.manifest['threshold']}")
    observed_b = observed_accuracy(strict, cases)
    print(f"ran DeepEval        observed accuracy = {observed_b:.4f}")
    print(f"verify (untouched)  -> {verify_observed(lock_b, observed_b)}   (honest miss)")

    # The dev quietly relaxes the DeepEval threshold to make CI green.
    gamed = dict(lock_b.manifest)
    gamed["threshold"] = 0.85
    print("…someone edits the locked threshold 0.95 -> 0.85 to flip it green…")
    verdict_b = verify_observed(lock_b, observed_b, current_manifest=gamed)
    print(f"verify (tampered)   -> {verdict_b}   (hash no longer matches the locked bar)")

    # ----- Result ------------------------------------------------------------
    ok = verdict_a == "PASS" and verdict_b == "TAMPERED"
    banner("RESULT")
    print(f"A honest claim   : {verdict_a}   (expected PASS)")
    print(f"B moved goalpost : {verdict_b}   (expected TAMPERED)")
    print("\nPRML caught the relaxed threshold a naive 'score >= threshold' "
          "check would have waved through." if ok else "\nUNEXPECTED — see above.")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
