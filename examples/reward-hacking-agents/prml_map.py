"""Map a RewardHackingAgents-style episode claim to a PRML pre-commitment.

RewardHackingAgents (Atinafu & Cohen, arXiv:2603.11337) measures evaluator
tampering in ML-engineering agents and shows that locking the evaluator
eliminates it (~50% of episodes -> 0). That lock protects the RUN, at
runtime, from the agent. This example adds the complementary layer: a
commitment that lets a third party verify, AFTER the fact, that the
episode's success criterion itself was fixed before the run and never
edited.

Offline and self-contained: no dataset download, no agent, no GPU. The
dataset hash below is computed over a synthetic stand-in file so the
example is runnable anywhere; in a real episode you would hash the
task's actual data split. Scenario numbers are illustrative.

Run:  python prml_map.py
"""
from __future__ import annotations

import copy
import hashlib
import os

from falsify_prml import evaluate_predicate, manifest_hash, validate_manifest

HERE = os.path.dirname(os.path.abspath(__file__))
DATASET = os.path.join(HERE, "credit_risk_split.csv")


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def lock_episode_claim() -> tuple[dict, str]:
    """Seal one episode's success criterion BEFORE the agent runs.

    In RewardHackingAgents terms: this is the bar the agent's reported
    metric will be graded against. The paper's evaluator lock keeps the
    agent from patching the grader; this manifest keeps ANYONE from
    quietly moving the bar afterwards — and proves it to a stranger.
    """
    manifest = {
        "version": "prml/0.1",
        "claim_id": "01900000-0000-7000-8000-00000048ac9e",  # UUIDv7 (schema-required)
        "created_at": "2026-08-11T12:00:00Z",
        "metric": "auc",
        "metric_args": {
            "rha_task": "credit_risk",
            "rha_variant": "hackable",
            "rha_trust_regime": "evalhashlock",
        },
        "comparator": ">=",
        "threshold": 0.70,
        "dataset": {"id": "rha/credit_risk@episode-split", "hash": sha256_file(DATASET)},
        "seed": 42,
        "producer": {"id": "examples/reward-hacking-agents (falsify)"},
    }
    errors = validate_manifest(manifest)
    if errors:
        raise SystemExit(f"invalid manifest: {errors}")
    return manifest, manifest_hash(manifest)


def main() -> int:
    manifest, digest = lock_episode_claim()
    print(f"[lock]   auc >= 0.70 sealed before the run   sha256 {digest[:16]}…")

    # Scenario A — honest episode: agent improves the model, observed 0.74
    observed = 0.74
    ok = manifest_hash(manifest) == digest and evaluate_predicate(
        observed, manifest["comparator"], manifest["threshold"])
    print(f"[A] observed auc = {observed:.2f}  -> {'PASS' if ok else 'FAIL'}")

    # Scenario B — the post-hoc move the runtime lock cannot testify about:
    # after a red result, someone edits the recorded bar down to 0.60.
    softened = copy.deepcopy(manifest)
    softened["threshold"] = 0.60
    tampered = manifest_hash(softened) != digest
    print(f"[B] bar edited 0.70 -> 0.60 after the run    -> "
          f"{'TAMPERED (hash mismatch)' if tampered else 'undetected'}")

    good = ok and tampered
    print("demo", "OK" if good else "BROKEN")
    return 0 if good else 1


if __name__ == "__main__":
    raise SystemExit(main())
