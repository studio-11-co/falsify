#!/usr/bin/env python3
"""hud <-> PRML bridge — lock the reward bar before the rollouts.

hud's Job is the receipt of the RUN: which rollouts happened, what rewards came
back. Nothing in that receipt says what the bar WAS before the rollouts — the
reward threshold that counts as success, the verifier that grades it, the task
arguments the claim is about. All of those are chosen by the party publishing
the number, and can be adjusted after the rewards are known. In RL-environment
evals that is not a corner case; moving the verifier or the pass bar after
seeing rollouts is exactly the failure mode agent leaderboards are fighting.

THE HONEST DESIGN (same split as our lm-eval bridge):
    lock   — BEFORE rollouts: build a PRML manifest from the hud Task itself
             (real `hud.eval.task.Task`, its real slug and args digest, the
             verifier's slug too) plus the reward threshold YOU choose, and
             lock it to a SHA-256. The bar is sealed before any rollout runs.
    verify — AFTER the Job finishes: read the job's mean reward and check it
             against the pre-locked manifest. Exit 0 PASS / 10 FAIL /
             3 TAMPERED (manifest edited after locking).

What is real vs modelled:
  - Task identity: REAL — `hud` SDK's own Task model builds the slugs
    (`id-<sha1_8(args)>`), and dataset.hash is a SHA-256 over the task's own
    canonical JSON (env, id, args, verifier). No API key needed: Task is pure
    data by hud's design.
  - PRML canonicalisation + hashing + verdicts: REAL `falsify_prml` reference.
  - The Job result: a faithful in-file sample of the fields this bridge reads
    (status / reward per run, mean reward), so the demo runs with no HUD
    account. Point --job-json at a real exported Job and it works the same.

Run:  python3 hud_to_prml.py            # lock -> (sample job) -> verify -> tamper demo
Needs: pip install hud falsify
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time

try:
    from hud.eval.task import Task
except ImportError:
    sys.exit("Needs the hud SDK: pip install hud")
try:
    import falsify_prml as prml
except ImportError:
    sys.exit("Needs the PRML reference: pip install falsify")


# A faithful sample of the Job fields this bridge reads (see hud/eval/job.py:
# per-run status + reward; Job.reward is the mean across graded runs).
SAMPLE_JOB = {
    "job_id": "sample-local",
    "runs": [
        {"status": "completed", "reward": 1.0},
        {"status": "completed", "reward": 1.0},
        {"status": "completed", "reward": 0.0},
        {"status": "completed", "reward": 1.0},
    ],
}


def uuid7(now_ms: int) -> str:
    """RFC 9562 UUIDv7 — PRML requires claim_id in this form."""
    b = bytearray(now_ms.to_bytes(6, "big") + os.urandom(10))
    b[6] = (b[6] & 0x0F) | 0x70
    b[8] = (b[8] & 0x3F) | 0x80
    h = bytes(b).hex()
    return f"{h[:8]}-{h[8:12]}-{h[12:16]}-{h[16:20]}-{h[20:]}"


def task_content_hash(task: Task) -> str:
    """SHA-256 over the task's own canonical JSON — env, id, args, verifier.

    This is the dataset-identity part of the claim: the exact task (and the
    exact verifier) the threshold is being promised against. hud already
    disambiguates args into the slug via a sha1_8; here the full definition is
    content-addressed so a swapped verifier or edited args cannot hide.
    """
    payload = task.model_dump(mode="json", include={"env", "id", "args", "verifier"})
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def build_manifest(task: Task, threshold: float, seed: int) -> dict:
    now_ms = int(time.time() * 1000)
    return {
        "version": "prml/0.1",
        "claim_id": uuid7(now_ms),
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now_ms // 1000)),
        "metric": "mean_reward",
        # the hud task (and verifier) the bar applies to, by name and by content
        "metric_args": {
            "hud_task": task.slug,
            "hud_verifier": task.verifier.slug if task.verifier else None,
        },
        "comparator": ">=",
        "threshold": float(threshold),
        "dataset": {"id": f"hud/{task.env}/{task.slug}", "hash": task_content_hash(task)},
        "seed": int(seed),
        "producer": {"id": "your-lab.dev"},
    }


def mean_reward(job: dict) -> float:
    graded = [r["reward"] for r in job.get("runs", [])
              if r.get("status") == "completed" and isinstance(r.get("reward"), (int, float))]
    if not graded:
        sys.exit("job has no graded runs")
    return sum(graded) / len(graded)


def verify(lock: dict, job: dict) -> int:
    m = lock["manifest"]
    if prml.manifest_hash(m) != lock["locked_sha256"]:
        print("  verdict : TAMPERED (exit 3) — manifest changed after lock")
        return 3
    observed = mean_reward(job)
    ok = prml.evaluate_predicate(observed, m["comparator"], m["threshold"])
    print(f"  observed: mean_reward = {observed}")
    print(f"  bar     : {m['comparator']} {m['threshold']}  on {m['metric_args']['hud_task']}")
    print(f"  verdict : {'PASS (exit 0)' if ok else 'FAIL (exit 10)'}")
    return 0 if ok else 10


def main() -> None:
    p = argparse.ArgumentParser(description="hud <-> PRML bridge")
    p.add_argument("--threshold", type=float, default=0.7)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--job-json", help="a real exported Job (defaults to the built-in sample)")
    args = p.parse_args()

    task = Task(
        env="browser-2048",
        id="reach-512",
        args={"target": 512, "max_steps": 80},
        verifier=Task(env="browser-2048", id="verify-board", args={"min_tile": 512}),
    )

    print("=" * 70)
    print("  hud  ->  PRML   (lock the reward bar before the rollouts)")
    print("=" * 70)
    print("\n[LOCK] before any rollout — seal the bar against the real hud Task")
    manifest = build_manifest(task, args.threshold, args.seed)
    errs = prml.validate_manifest(manifest)
    if errs:
        sys.exit("invalid manifest: " + "; ".join(errs))
    lock = {"manifest": manifest, "locked_sha256": prml.manifest_hash(manifest)}
    print(f"  task    : {manifest['dataset']['id']}   (verifier {manifest['metric_args']['hud_verifier']})")
    print(f"  bar     : mean_reward >= {args.threshold}   seed={args.seed}")
    print(f"  locked  : sha256:{lock['locked_sha256'][:20]}…")

    job = json.load(open(args.job_json)) if args.job_json else SAMPLE_JOB
    print(f"\n[RUN]  hud Job finishes ({'real job' if args.job_json else 'built-in sample'})")

    print("\n[VERIFY] after the job — check the mean reward against the sealed bar")
    rc = verify(lock, job)

    print("\n[ADVERSARIAL] the verifier is quietly swapped after seeing rewards")
    moved = json.loads(json.dumps(lock))
    moved["manifest"]["metric_args"]["hud_verifier"] = "verify-board-easier-00000000"
    rc2 = verify(moved, job)
    print("  -> the Job receipt alone cannot catch this; the locked manifest does"
          f" (exit {rc2}).")
    print("=" * 70)
    sys.exit(rc)


if __name__ == "__main__":
    main()
