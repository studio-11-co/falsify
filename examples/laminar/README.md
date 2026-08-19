# Laminar + PRML: lock the eval bar before `evaluate()` runs

[Laminar](https://github.com/lmnr-ai/lmnr) records what an eval produced:
executor outputs, evaluator scores, `average_scores`. What no run record can
say about itself is what the bar **was** before the run — which evaluator
decides the claim, what threshold counts as success, which dataset the claim
is about. Every one of those is chosen by the party publishing the number, and
can be adjusted after the score is known.

[PRML](https://spec.falsify.dev) locks exactly that: the success criteria of
an evaluation, committed to a SHA-256 over canonical bytes **before** the run,
independently verifiable offline afterwards.

## What the bridge does

```
lock    before the run: manifest binds evaluator name (= average_scores key),
        comparator + threshold, sha256(canonical JSON of the dataset), seed
verify  after the run:  average_scores[metric] vs the pre-locked bar
        exit 0 PASS · 10 FAIL · 3 TAMPERED (manifest edited after locking)
```

## Run it

```sh
pip install lmnr falsify
python3 laminar_prml.py
```

Expected output ends with a PASS verdict and a caught tamper attempt:

```
observed exact_match = 0.75  vs locked bar >= 0.7
verdict: PASS

-- adversarial: threshold edited 0.7 -> 0.5 AFTER the run --
verdict: TAMPERED — manifest does not match the pre-run lock
```

## What is real vs modelled

- **Scoring semantics: real `lmnr` SDK.** Evaluators are invoked with the
  SDK's own calling convention (`evaluator(output, target)`; numeric return
  keyed by evaluator name, dict merged as-is), results are real
  `EvaluationResultDatapoint` objects, and the aggregate comes from the SDK's
  own `get_average_scores` — imported, not imitated. Verified against
  lmnr 0.7.42 from PyPI in a clean environment.
- **PRML side: real `falsify` reference implementation** (canonical bytes,
  manifest hash, verdict codes).
- **Not exercised: the platform upload.** `evaluate()` needs a Laminar
  backend; this demo stops at the boundary where scores leave the process.
  The lock/verify split is unchanged when the full pipeline runs — the
  manifest never depends on where scores are displayed.

The evaluator here is judge-free (exact match) so the demo is deterministic
and the only thing under discussion is the bar. With an LLM judge the lock
matters *more*, not less: the judge's identity belongs in `metric_args` and
the threshold still has to predate the scores.
