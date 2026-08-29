# DeepEval × PRML — lock the bar before DeepEval scores it

[DeepEval](https://github.com/confident-ai/deepeval) gives you the **score**.
PRML locks the **bar that score has to beat** — metric, comparator, threshold,
exact dataset bytes, seed, producer — to a SHA-256 *before* the evaluation runs.
Relax a DeepEval `threshold` after seeing a red result and the hash stops
matching: the claim reads **TAMPERED**, not PASS.

This is a complete, **offline, deterministic** example — no LLM, no API key, no
network. It uses DeepEval's real SDK (`LLMTestCase`, `BaseMetric`) and the PRML
reference package (`falsify`). Everything below is reproduced byte-for-byte by
`python run_with_prml.py`.

## Why DeepEval specifically

Every DeepEval metric carries a `threshold`, and `success = score >= threshold`.
That threshold is exactly the knob a benchmark gets gamed on: a run fails at
`0.95`, so someone quietly edits it to `0.85` and CI goes green. A naive
`score >= threshold` check can't tell a pre-committed bar from one lowered after
the fact. PRML can — because the bar was sealed to a hash before the run.

## Files

| File | What it is |
|---|---|
| `prml_deepeval.py` | The bridge: `lock_metric()` seals a DeepEval metric's bar into a PRML manifest before the run; `verify_observed()` grades the score after, returning `PASS` / `FAIL` / `TAMPERED`. Pure functions only — no CLI, no network. |
| `exact_match_metric.py` | A deterministic, LLM-free DeepEval `BaseMetric` (normalized exact match) so the example runs identically everywhere. |
| `eval_set.jsonl` | 10 real QA cases — 9 exact matches → accuracy `0.90`. SHA-256 `3cb8ff9b4920b7624a00ccba387d10424a2fdf50bb4cb33c7fb9c9e3d69671c2`. |
| `run_with_prml.py` | The two-scenario demo below. |

## Run it

```bash
pip install -r requirements.txt
python run_with_prml.py
```

## Verified output

```
================================================================
A. Honest claim — accuracy >= 0.85
================================================================
locked BEFORE run   sha256=8df7620946801b9de5e3c29ae10deee9c8fc062c3fc0cede17694b09bfa04b42
  bar: accuracy >= 0.85   dataset=3cb8ff9b4920b762…
ran DeepEval        observed accuracy = 0.9000
verify -> PASS

================================================================
B. Gamed run — lock 0.95, miss, then lower the bar to 0.85
================================================================
locked BEFORE run   sha256=056e32e9d19637b33ab4a0f334e9e0ea91dbb75fa1355784a59503099316209c
  bar: accuracy >= 0.95
ran DeepEval        observed accuracy = 0.9000
verify (untouched)  -> FAIL   (honest miss)
…someone edits the locked threshold 0.95 -> 0.85 to flip it green…
verify (tampered)   -> TAMPERED   (hash no longer matches the locked bar)

================================================================
RESULT
================================================================
A honest claim   : PASS   (expected PASS)
B moved goalpost : TAMPERED   (expected TAMPERED)
```

Scenario **B** is the whole point: the observed score (`0.90`) never changed.
Only the *bar* moved — and because the bar was locked to `056e32e9…` before the
run, moving it is detectable from the manifest alone, by anyone, offline.

## The integration in three lines

```python
from prml_deepeval import lock_metric, verify_observed

lock = lock_metric(metric, claim_id=..., metric_id="accuracy", created_at=...,
                   dataset_path=..., dataset_id=..., seed=42, producer_id=...)  # BEFORE run
observed = run_your_deepeval_evaluation(metric)                                 # DeepEval as usual
verdict = verify_observed(lock, observed)   # PASS / FAIL / TAMPERED            # AFTER run
```

## What this does and does not prove

- **Does:** prove the bar (`threshold`, `metric`, `comparator`, `dataset.hash`,
  `seed`, `producer`) was fixed before the score was known. Moving any bound
  field after the lock is detectable.
- **Does not:** prove the score itself is correct, or that the producer ran the
  eval at all, or published every claim. Those need execution attestation and a
  publication anchor — see the PRML spec §8.1 and `docs/EMBED.md`.

PRML proves the *bar was locked*, never the *result*.

---

*Part of [`studio-11-co/falsify`](https://github.com/studio-11-co/falsify). Spec:
[spec.falsify.dev/v0.1](https://spec.falsify.dev/v0.1) · Community Specification License 1.0. Reference
implementation MIT. DeepEval is © Confident AI, Apache-2.0 — this example
depends on it, and is not affiliated with or endorsed by Confident AI.*
