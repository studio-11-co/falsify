# Braintrust / autoevals + PRML — lock the bar, then evaluate

A pre-registered eval run on top of [autoevals](https://github.com/braintrustdata/autoevals):
the success criteria (metric, comparator, threshold, dataset hash, seed) are
locked to a SHA-256 **before** the run, and the verdict is computed against
the locked bar, never a live one. Move the bar after the results are in and
the run refuses to score (exit 3, TAMPERED).

Runs fully offline, no API keys:

```bash
pip install falsify autoevals
python locked_eval.py
```

```
metric:    levenshtein_mean over 8 rows (autoevals Levenshtein)
observed:  0.9934
locked:    >= 0.85  (sha256 0720f9ce23d8..., created 2026-07-21T12:00:00Z)
verdict:   PASS
```

## What the run enforces

| Check | Failure mode it catches | Exit |
|---|---|---|
| Manifest hash vs locked hash | threshold/metric edited after locking | 3 TAMPERED |
| Dataset SHA-256 vs `dataset.hash` | eval data swapped after locking | 3 |
| Predicate vs **locked** threshold | score below the pre-registered bar | 10 FAIL |

Try it: change `threshold:` in `manifest.prml.yaml` and run again.

## Files

- `manifest.prml.yaml` — the locked claim ([PRML v0.1](https://spec.falsify.dev/v0.1), 9 fields)
- `dataset.jsonl` — the eval set the manifest's `dataset.hash` pins
- `locked_eval.py` — hash check, dataset check, autoevals scoring, locked verdict

## Using it with a real Braintrust experiment

Replace `demo_model()` with your task and attach the locked hash to the
experiment so every logged run is bound to its pre-registered bar:

```python
import braintrust

experiment = braintrust.init(
    project="my-project",
    metadata={"prml_manifest_hash": LOCKED_HASH,
              "prml_spec": "https://spec.falsify.dev/v0.1"},
)
```

For a public, independently timestamped receipt of the lock (RFC 3161 +
Rekor transparency log), commit the manifest at
[registry.falsify.dev](https://registry.falsify.dev) before the run.

## Scope

PRML proves the bar was locked before the run. It never proves the observed
score is correct — that stays with your eval infrastructure. Spec CC BY 4.0,
implementations MIT.
