"""Verify a Hugging Face lighteval run against a PRML pre-commitment —
using the UNMODIFIED falsify-inspect adapter.

lighteval's `eval` backend is built on the UK AI Security Institute's
Inspect framework, and its log output is Inspect's log schema. That
convergence means the existing falsify-inspect adapter verifies lighteval
runs out of the box: lock the bar before `lighteval eval`, verify the log
it writes afterwards.

Offline by default: verifies the bundled fixture log (a real lighteval
0.13 output, mockllm backend, gsm8k, 4 samples). See README for the live
two-command flow.

Run:  pip install falsify-inspect && python lock_and_verify.py
"""
from __future__ import annotations

import os

from falsify_inspect import preregister, verify_eval_log

HERE = os.path.dirname(os.path.abspath(__file__))
LOG = os.path.join(HERE, "fixture_lighteval_log.json")

# Illustrative: mockllm answers nothing correctly, so the honest bar for
# this demo is an upper bound ("error stays under 10%" inverted: accuracy
# <= 0.10 would be a strange real claim — here it simply makes the demo's
# PASS/TAMPERED mechanics visible with the fixture's observed 0.0).
DATASET_HASH = "b" * 64  # real usage: SHA-256 of the pinned dataset revision


def main() -> int:
    h, m = preregister(
        metric="math_scorer",
        threshold=0.10,
        threshold_direction="<=",
        dataset="openai/gsm8k",
        dataset_hash=DATASET_HASH,
        model_version="mockllm/model",
        sample_size=1,
        seed=0,
        pre_registered="2026-08-11T00:00:00Z",
        inspect_task="gsm8k",
    )
    print(f"[lock]   math_scorer <= 0.10 sealed   sha256 {h[:16]}…")

    r = verify_eval_log(
        LOG,
        expected_hash=h,
        threshold=0.10,
        threshold_direction="<=",
        pre_registered="2026-08-11T00:00:00Z",
        claim_id=m.claim_id,
        dataset_hash=DATASET_HASH,
        seed=0,
    )
    print(f"[verify] hash_match={r['hash_match']} observed={r['observed_value']} -> "
          f"{'PASS' if r['ok'] else 'FAIL/TAMPERED'}")

    # The tamper case: verify against a quietly-softened bar.
    r2 = verify_eval_log(
        LOG,
        expected_hash=h,
        threshold=0.50,          # bar moved after the fact
        threshold_direction="<=",
        pre_registered="2026-08-11T00:00:00Z",
        claim_id=m.claim_id,
        dataset_hash=DATASET_HASH,
        seed=0,
    )
    print(f"[tamper] threshold edited 0.10 -> 0.50 -> hash_match={r2['hash_match']} "
          f"({'TAMPERED detected' if not r2['hash_match'] else 'undetected'})")

    ok = r["ok"] and not r2["hash_match"]
    print("demo", "OK" if ok else "BROKEN")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
