"""Bridge lm-evaluation-harness runs to PRML pre-registration.

The harness tells you the *score*. PRML locks the *bar that score must beat* —
the metric, the comparator, the threshold, the exact dataset bytes, the seed,
the producer — to a SHA-256 **before** the run. After the run you verify the
observed score against that locked manifest. If anyone edits the threshold (or
any other bound field) between lock and verify — the classic move of quietly
relaxing the bar after seeing a red result — the hash no longer matches and the
claim reads TAMPERED instead of PASS.

Harness-specific detail worth locking: the task configuration itself. A task
YAML controls the prompt template, the split, the metric aggregation and the
generation settings — all of which move the score. This bridge hashes the task
config and binds it inside ``metric_args``, so "same task" is a checkable
claim, not a social one.

Depends only on the PRML reference package (``falsify``): three pure functions,
no CLI, no network, no account.

    validate_manifest(manifest) -> list[str]   # [] means valid
    manifest_hash(manifest)     -> str         # 64-hex SHA-256 over canonical bytes
    evaluate_predicate(observed, comparator, threshold) -> bool
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass

from falsify_prml import evaluate_predicate, manifest_hash, validate_manifest


def sha256_file(path: str) -> str:
    """SHA-256 of a file's bytes — used for dataset and task-config binding."""
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


def lock_harness_claim(
    *,
    claim_id: str,
    created_at: str,
    task: str,
    task_config_path: str,
    metric: str,
    comparator: str,
    threshold: float,
    dataset_id: str,
    dataset_path: str,
    seed: int,
    producer_id: str,
) -> PrmlLock:
    """Seal an lm-eval-harness claim into a PRML manifest BEFORE the run.

    ``dataset_path`` is the local dataset file the toy task reads; for a real
    Hub-hosted task, put the dataset's content digest (or the revision commit
    you resolved) here instead — the point is that the bytes you will be graded
    on are named before the run. ``seed`` should be the same value passed to
    the harness (``--seed`` / ``simple_evaluate(random_seed=...)``).
    """
    manifest = {
        "version": "prml/0.1",
        "claim_id": claim_id,
        "created_at": created_at,
        "metric": metric,
        "metric_args": {
            "lm_eval_task": task,
            "task_config_sha256": sha256_file(task_config_path),
        },
        "comparator": comparator,
        "threshold": float(threshold),
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
