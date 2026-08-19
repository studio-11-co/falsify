# Langfuse + PRML: lock the experiment bar before the run

A [Langfuse](https://github.com/langfuse/langfuse) experiment records what
happened — task outputs, item evaluations, run-level aggregates. What no
experiment record can say about itself is what the bar **was** before the run:
which evaluator decides the claim, what aggregate counts as success, which
items (by content, not by dataset name) the claim is about. Each of those is
chosen by the party publishing the number, and can be adjusted after the
aggregate is known.

[PRML](https://spec.falsify.dev) locks exactly that: the success criteria,
committed to a SHA-256 over canonical bytes **before** the run, independently
verifiable offline afterwards.

## What the bridge does

```
lock    before: manifest binds the run-level evaluation name, comparator +
        threshold, sha256(canonical JSON of the items), seed
run     the experiment, through the SDK's own task/evaluator machinery
verify  after: the run-level aggregate vs the pre-locked bar
        exit 0 PASS · 10 FAIL · 3 TAMPERED
```

## Run it

```sh
pip install langfuse falsify
python3 langfuse_prml.py
```

Expected output ends with a PASS verdict and a caught tamper attempt:

```
observed pass_rate = 0.75  vs locked bar >= 0.7
verdict: PASS

-- adversarial: threshold edited 0.7 -> 0.5 AFTER the run --
verdict: TAMPERED — manifest does not match the pre-run lock
```

## What is real vs modelled

- **Execution and scoring semantics: real `langfuse` SDK.** Tasks and
  evaluators run through the SDK's own `_run_task` / `_run_evaluator` — the
  same normalization `run_experiment` uses (sync/async handling, Evaluation
  lists) — results are real `ExperimentItemResult` objects, evaluations real
  `langfuse.Evaluation` instances, and the aggregate is a run-level evaluator
  in exactly the documented shape (`def pass_rate(*, item_results, **kwargs)`).
  Imported, not imitated. Verified against langfuse 4.14.4 from PyPI in a
  clean environment; all three verdict paths exercised.
- **PRML side: real `falsify` reference** (canonical bytes, manifest hash,
  verdict codes).
- **Not exercised: the platform upload.** `run_experiment` logs to a Langfuse
  backend; this demo stops at the boundary where results leave the process.
  The lock/verify split is unchanged when the full pipeline runs — the
  manifest never depends on where results are displayed.

The evaluator here is judge-free (exact match) so the demo is deterministic
and the only thing under discussion is the bar. With an LLM judge the lock
matters *more*, not less: the judge's identity belongs in `metric_args` and
the threshold still has to predate the scores.
