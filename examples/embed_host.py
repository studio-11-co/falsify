#!/usr/bin/env python3
"""embed_host.py — what it looks like for a host to embed PRML. Runnable.

This is the working companion to docs/EMBED.md. It plays the role of an eval /
governance platform ("AcmeEval") that wraps a customer's evaluation run with a
PRML pre-registration, using ONLY the three public functions plus the in-toto
bridge — no PRML CLI, no new format.

The flow a host actually wires in:
    1. lock   — BEFORE the run: validate + hash the claim, store the lock.
    2. run    — the host's normal eval (here: a stand-in that returns a number).
    3. verify — AFTER the run: re-hash (tamper check) + evaluate the predicate.
    4. attest — emit an in-toto (ITE-6) Statement for the host's evidence bundle.

Run:  pip install falsify  &&  python3 embed_host.py
Requires only `falsify` (ships falsify_prml). No other dependencies.
"""
import json
import os
import sys

try:
    import falsify_prml as prml
except ImportError:
    # fall back to the repo checkout if not pip-installed
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
    try:
        import falsify_prml as prml
    except ImportError:
        sys.exit("needs the PRML reference — run: pip install falsify")


# ── 1. the claim the customer pre-registers (a plain dict; 9 required fields) ──
CLAIM = {
    "version": "prml/0.1",
    "claim_id": "019212aa-4b00-7c00-8000-00000000ac2e",  # UUIDv7 (schema requirement as of v0.3.12)
    "created_at": "2026-06-18T00:00:00Z",
    "metric": "accuracy",
    "comparator": ">=",
    "threshold": 0.90,
    "dataset": {"id": "imagenet-val-2012",
                "hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"},
    "seed": 42,
    "producer": {"id": "acme.ai"},
}


class AcmeEval:
    """A stand-in for a host platform embedding PRML. Three of its methods are
    the entire integration; the 'run' is whatever the host already does."""

    def lock(self, claim: dict) -> str:
        errs = prml.validate_manifest(claim)
        if errs:
            raise ValueError("AcmeEval refuses to start a run on an invalid claim: "
                             + "; ".join(errs))
        lock = prml.manifest_hash(claim)
        print(f"[lock]   bar sealed BEFORE the run  metric={claim['metric']} "
              f"{claim['comparator']} {claim['threshold']}  sha256={lock[:16]}…")
        return lock

    def run(self, claim: dict) -> float:
        # The host's real eval goes here. Stand-in: a deterministic number.
        observed = 0.934
        print(f"[run]    eval produced  {claim['metric']} = {observed}")
        return observed

    def verify(self, claim: dict, locked: str, observed: float) -> str:
        if prml.manifest_hash(claim) != locked:
            print("[verify] TAMPERED — the claim changed after locking (exit-equivalent 3)")
            return "TAMPERED"
        ok = prml.evaluate_predicate(observed, claim["comparator"], claim["threshold"])
        verdict = "PASS" if ok else "FAIL"
        print(f"[verify] {verdict}  ({observed} {claim['comparator']} {claim['threshold']})")
        return verdict

    def attest(self, claim: dict) -> dict:
        stmt = prml.to_intoto_statement(claim)
        print(f"[attest] in-toto {stmt['_type'].rsplit('/', 2)[-2]}/"
              f"{stmt['_type'].rsplit('/', 1)[-1]}  predicateType={stmt['predicateType']}")
        return stmt


def main():
    print("=" * 70)
    print("  AcmeEval — a host embedding PRML (docs/EMBED.md, runnable)")
    print("=" * 70)
    host = AcmeEval()

    lock = host.lock(CLAIM)                    # 1. before the run
    observed = host.run(CLAIM)                 # 2. the run
    host.verify(CLAIM, lock, observed)         # 3. after the run
    stmt = host.attest(CLAIM)                  # 4. evidence for the bundle

    # The attestation is self-anchoring: its subject digest IS the lock.
    assert stmt["subject"][0]["digest"]["sha256"] == lock
    print("\n[check]  attestation subject digest == the lock  ✓ (self-anchoring)")

    print("\n[adversarial] someone relaxes the threshold 0.90 → 0.80 after locking")
    moved = json.loads(json.dumps(CLAIM)); moved["threshold"] = 0.80
    host.verify(moved, lock, observed)         # → TAMPERED, even though 0.934 ≥ 0.80

    print("\n--- the in-toto Statement a host drops into its evidence bundle ---")
    print(json.dumps(stmt, indent=2, sort_keys=True))
    print("=" * 70)


if __name__ == "__main__":
    main()
