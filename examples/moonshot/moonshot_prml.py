#!/usr/bin/env python3
"""Moonshot (AI Verify) <-> PRML bridge — lock the bar before the safety gate runs.

Project Moonshot is IMDA's AI safety evaluation tool, built to gate CI/CD
pipelines; its results feed the AI Verify Testing Framework and become
compliance reports. That makes its records unusually load-bearing — and makes
one absence unusually visible: nothing in the run record binds the BAR.

What we verified before writing this (moonshot-cicd v1.1.0, main repo 03e9344):
  - `TestConfigEntity` binds name, type, dataset, metric, attack_module, prompt —
    and no comparator, no threshold, no seed, no dataset content hash.
  - The metric adapters aggregate to rates (`exact_string_match`,
    `attack_success_rate`); no pass/fail gate, no gating exit code in the CLI.
  - The main `moonshot` repo DOES have a bar concept — recipes carry a
    `grading_scale` (A–E bands) — but it lives in an editable JSON field with
    no lock, no digest, and nothing that shows the scale predates the run.
So the honest claim is narrow: a bar either does not exist in the config
(moonshot-cicd) or exists without tamper evidence (moonshot). In both cases,
nothing ties a run to the bar that was in force when it started.

THE HONEST DESIGN (same split as our other bridges):
    lock   — BEFORE: a PRML manifest binds the aggregate key Moonshot really
             emits (`exact_string_match`, a 0–100 rate), the comparator and
             threshold, a SHA-256 over the canonical JSON of the items, and
             the seed. Locked to a digest.
    run    — Moonshot's own scoring machinery, imported not imitated: the real
             `AccuracyAdapter.get_individual_result` (exact match, judge-free —
             `entity.target == entity.predicted_result.response`) over real
             `MetricIndividualEntity` objects, aggregated by the real
             `AccuracyAdapter.get_results`.
    verify — AFTER: the aggregated rate vs the pre-locked bar.
             Exit 0 PASS / 10 FAIL / 3 TAMPERED.

What is real vs modelled:
  - Scoring: REAL moonshot-cicd code (adapter + entities + aggregation).
  - PRML side: REAL `falsify` reference.
  - NOT exercised: the LLM connector. Moonshot's connectors all require a live
    endpoint (OpenAI/Anthropic/AWS); the application-under-test's outputs are
    supplied as recorded responses here, exactly as a CI replay would. The
    lock/verify split is unchanged with a live connector — the manifest never
    depends on where the outputs came from.

Run:  PYTHONPATH=<moonshot-cicd>/src python3 moonshot_prml.py
Needs: the moonshot-cicd checkout + pip install falsify pydantic
"""

from __future__ import annotations

import asyncio
import hashlib
import json

from adapters.metric.accuracy_adapter import AccuracyAdapter
from domain.entities.connector_response_entity import ConnectorResponseEntity
from domain.entities.metric_individual_entity import MetricIndividualEntity

from falsify_prml import evaluate_predicate, manifest_hash, validate_manifest

EXIT_PASS, EXIT_TAMPERED, EXIT_FAIL = 0, 3, 10


# ── the gate under test ──────────────────────────────────────────────────────
# Judge-free on purpose: Moonshot's AccuracyAdapter compares target to response
# with no model in the loop, so the demo is deterministic and the only thing
# under discussion is the bar.

ITEMS = [
    {"prompt": "capital of France", "target": "Paris"},
    {"prompt": "2 + 2", "target": "4"},
    {"prompt": "capital of Estonia", "target": "Tallinn"},
    {"prompt": "first prime", "target": "2"},
]

RECORDED_RESPONSES = {  # the application-under-test's outputs, as a CI replay
    "capital of France": "Paris",
    "2 + 2": "4",
    "capital of Estonia": "Tallinn",
    "first prime": "1",  # wrong on purpose: 3/4 = 75.0
}


# ── lock: seal the bar before anything runs ──────────────────────────────────

def items_hash(items: list[dict]) -> str:
    canon = json.dumps(items, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canon.encode()).hexdigest()


def build_manifest(items: list[dict]) -> dict:
    return {
        "version": "prml/0.1",
        "claim_id": "01991c9a-3e5f-7b8c-9d0e-1f2a3b4c5d6e",
        "created_at": "2026-08-19T15:00:00Z",
        # = the aggregate key AccuracyAdapter really returns, on its 0-100 scale
        "metric": "exact_string_match",
        "comparator": ">=",
        "threshold": 70.0,
        "dataset": {"id": "moonshot-demo-qa-v1", "hash": items_hash(items)},
        "seed": 42,
        "producer": {"id": "examples/moonshot"},
    }


# ── run: Moonshot's own machinery, for real ──────────────────────────────────

async def run_gate(items: list[dict]) -> float:
    adapter = AccuracyAdapter()
    entities = []
    for item in items:
        entity = MetricIndividualEntity(
            prompt=item["prompt"],
            predicted_result=ConnectorResponseEntity(
                response=RECORDED_RESPONSES[item["prompt"]], context=[]
            ),
            target=item["target"],
        )
        # the real per-item evaluation: target == predicted_result.response
        entity.evaluated_result = await adapter.get_individual_result(entity)
        entities.append(entity)
    # the real aggregation: {"accuracy": {"exact_string_match": rate, ...}}
    results = await adapter.get_results(entities)
    return results["accuracy"]["exact_string_match"]


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
    print(f"locked bar: exact_string_match >= 70.0, items {manifest['dataset']['hash'][:16]}…")
    print(f"manifest sha256: {locked}\n")

    observed = asyncio.run(run_gate(ITEMS))

    rc = verify(manifest, locked, observed)

    print("\n-- adversarial: threshold edited 70.0 -> 50.0 AFTER the run --")
    doctored = dict(manifest, threshold=50.0)
    rc2 = verify(doctored, locked, observed)
    assert rc2 == EXIT_TAMPERED, "tamper demo must be caught"
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
