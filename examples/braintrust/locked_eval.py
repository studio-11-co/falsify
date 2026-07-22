#!/usr/bin/env python3
"""Pre-registered Braintrust/autoevals run: lock the bar, then evaluate.

Runs an autoevals scorer over a dataset and verifies the aggregate score
against a PRML manifest that was locked BEFORE the run. Three properties a
plain eval script does not have:

  1. The dataset is content-checked against the locked dataset.hash.
  2. The success criteria (metric, comparator, threshold, seed) are hashed
     before the run; editing them afterwards is detectable (exit 3 TAMPERED).
  3. The verdict is computed against the LOCKED threshold, never a live one.

Exit codes (the PRML contract): 0 PASS · 3 TAMPERED · 10 FAIL · 2 bad input.

Runs fully offline: the demo "model" is a lookup table and the scorer is
autoevals' Levenshtein, so no API keys are needed. With a real model, replace
`demo_model()`; nothing else changes. To also log the experiment to Braintrust
with the locked hash attached, see README.md.

    pip install falsify autoevals
    python locked_eval.py
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

from autoevals import Levenshtein
from falsify_prml import evaluate_predicate, load_manifest, manifest_hash, validate_manifest

HERE = Path(__file__).parent
MANIFEST = HERE / "manifest.prml.yaml"
DATASET = HERE / "dataset.jsonl"

# The hash this run is bound to. In CI you would pin this via
# `falsify lock` + the sidecar, or a registry receipt; pinning it in the
# runner keeps the example self-contained.
LOCKED_HASH = "0720f9ce23d8c7ac90ee438434953cd11c2b977255c391b771932c93fbd1053b"


def demo_model(question: str) -> str:
    """Stand-in for the model under test. Deliberately imperfect: one answer
    is misspelled so the aggregate lands near, not at, 1.0."""
    answers = {
        "What is the capital of France?": "Paris",
        "What is 6 times 7?": "42",
        "Which planet is known as the Red Planet?": "Mars",
        "What is the chemical symbol for gold?": "Au",
        "In which year did the Berlin Wall fall?": "1989",
        "What is the largest ocean on Earth?": "Pacific Ocean",
        "Who wrote the play Hamlet?": "William Shakespare",  # sic
        "What is the boiling point of water in Celsius?": "100",
    }
    return answers.get(question, "")


def main() -> int:
    # 1. Load and validate the locked manifest.
    manifest = load_manifest(str(MANIFEST))
    errors = validate_manifest(manifest)
    if errors:
        print("invalid manifest:", "; ".join(errors))
        return 2

    # 2. Tamper check: does the manifest still hash to what was locked?
    current = manifest_hash(manifest)
    if current != LOCKED_HASH:
        print("TAMPERED")
        print(f"  locked:     {LOCKED_HASH}")
        print(f"  recomputed: {current}")
        print("  The success criteria changed after locking. Refusing to score.")
        return 3

    # 3. Dataset content check against the locked digest (spec 5.2 step 2).
    ds_digest = hashlib.sha256(DATASET.read_bytes()).hexdigest()
    if ds_digest != manifest["dataset"]["hash"]:
        print("DATASET MISMATCH")
        print(f"  locked:     {manifest['dataset']['hash']}")
        print(f"  recomputed: {ds_digest}")
        return 3

    # 4. Run the eval: autoevals scorer over every row.
    scorer = Levenshtein()
    rows = [json.loads(line) for line in DATASET.read_text().splitlines() if line.strip()]
    scores = []
    for row in rows:
        result = scorer(output=demo_model(row["input"]), expected=row["expected"])
        scores.append(result.score)
    observed = sum(scores) / len(scores)

    # 5. Verdict against the LOCKED bar, not a live one.
    ok = evaluate_predicate(observed, manifest["comparator"], manifest["threshold"])
    print(f"metric:    {manifest['metric']} over {len(rows)} rows (autoevals Levenshtein)")
    print(f"observed:  {observed:.4f}")
    print(f"locked:    {manifest['comparator']} {manifest['threshold']}  (sha256 {LOCKED_HASH[:12]}..., "
          f"created {manifest['created_at']})")
    print("verdict:   " + ("PASS" if ok else "FAIL"))
    return 0 if ok else 10


if __name__ == "__main__":
    sys.exit(main())
