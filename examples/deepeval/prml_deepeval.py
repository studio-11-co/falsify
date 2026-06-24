"""Bridge DeepEval metrics to PRML pre-registration.

DeepEval tells you the *score*. PRML locks the *bar that score must beat* — the
metric, the comparator, the threshold, the exact dataset bytes, the seed, the
producer — to a SHA-256 **before** the evaluation runs. After the run you verify
the observed score against that locked manifest. If anyone edits the threshold
(or any other bound field) between lock and verify — the classic move of quietly
relaxing a DeepEval `threshold` after seeing a red result — the hash no longer
matches and the claim reads TAMPERED instead of PASS.

Depends only on the PRML reference package (`falsify`): three pure functions,
no CLI, no network, no account.

    validate_manifest(manifest) -> list[str]   # [] means valid
    manifest_hash(manifest)     -> str         # 64-hex SHA-256 over canonical bytes
    evaluate_predicate(observed, comparator, threshold) -> bool
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass

from deepeval.metrics import BaseMetric
from falsify_prml import evaluate_predicate, manifest_hash, validate_manifest


def sha256_file(path: str) -> str:
    """SHA-256 of a dataset file's bytes — the `dataset.hash` PRML binds."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


@dataclass(frozen=True)
class PrmlLock:
    """The sealed claim: the manifest as locked, plus its canonical digest."""

    manifest: dict
    digest: str


def lock_metric(
    metric: BaseMetric,
    *,
    claim_id: str,
    metric_id: str,
    created_at: str,
    dataset_path: str,
    dataset_id: str,
    seed: int,
    producer_id: str,
) -> PrmlLock:
    """Seal a DeepEval metric's bar into a PRML manifest BEFORE the run.

    The threshold is read straight from ``metric.threshold`` — so the number you
    will be graded against is committed now, not chosen after you see the score.
    DeepEval's success rule is ``score >= threshold``; PRML records that as the
    ``>=`` comparator so the two agree by construction.
    """
    manifest = {
        "version": "prml/0.1",
        "claim_id": claim_id,
        "created_at": created_at,
        "metric": metric_id,
        "comparator": ">=",
        "threshold": float(metric.threshold),
        "dataset": {"id": dataset_id, "hash": sha256_file(dataset_path)},
        "seed": seed,
        "producer": {"id": producer_id},
    }
    errors = validate_manifest(manifest)
    if errors:
        raise ValueError(f"PRML manifest invalid: {errors}")
    return PrmlLock(manifest=manifest, digest=manifest_hash(manifest))


def verify_observed(
    lock: PrmlLock, observed: float, *, current_manifest: dict | None = None
) -> str:
    """Grade an observed score against a locked claim. Returns PASS / FAIL / TAMPERED.

    ``current_manifest`` is the claim as it stands at verify time. If it differs
    from what was locked — e.g. someone lowered the threshold after seeing a
    failing score — its hash won't match ``lock.digest`` and the result is
    TAMPERED, regardless of whether the softened bar would have "passed".
    """
    manifest = current_manifest if current_manifest is not None else lock.manifest
    if manifest_hash(manifest) != lock.digest:
        return "TAMPERED"
    passed = evaluate_predicate(observed, manifest["comparator"], manifest["threshold"])
    return "PASS" if passed else "FAIL"
