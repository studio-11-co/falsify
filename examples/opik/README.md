# Opik + PRML: lock the eval bar before the metrics run

[Opik](https://github.com/comet-ml/opik) records what an eval produced —
test results, aggregated score statistics. What no run record can say about
itself is what the bar **was** before the run: which metric decides the claim,
what mean counts as success, which items (by content, not by name) the claim
is about. Every one of those is chosen by the party publishing the number, and
can be adjusted after the mean is known.

[PRML](https://spec.falsify.dev) locks exactly that: the success criteria,
committed to a SHA-256 over canonical bytes **before** the run, independently
verifiable offline afterwards.

## What the bridge does

```
lock    before: manifest binds the metric name (= the aggregated_scores key),
        comparator + threshold, sha256(canonical JSON of the items), seed
run     Opik's own `evaluate_on_dict_items` — their public, platform-free
        evaluation entry point — with the real `Equals` metric and the real
        `aggregate_evaluation_scores()`
verify  after: the aggregated mean vs the pre-locked bar
        exit 0 PASS · 10 FAIL · 3 TAMPERED
```

## Run it

```sh
pip install opik falsify
OPIK_TRACK_DISABLE=true python3 opik_prml.py
```

Expected output ends with a PASS verdict and a caught tamper attempt:

```
observed equals_metric mean = 0.75  vs locked bar >= 0.7
verdict: PASS

-- adversarial: threshold edited 0.7 -> 0.5 AFTER the run --
verdict: TAMPERED — manifest does not match the pre-run lock
```

## What is real

The whole scoring path is Opik's own, imported rather than imitated:
`evaluate_on_dict_items` (which Opik ships precisely for platform-free
evaluation — "without requiring a Dataset object or creating an experiment"),
the `Equals` heuristic metric, and `aggregate_evaluation_scores()`. Verified
against opik 2.2.31 + falsify 0.3.12 from PyPI in a clean environment; all
three verdict paths exercised.

One honest note on tracing: the evaluation engine still creates trace records,
and without an API key the background uploads are rejected with a 401 and
dropped — harmless, nothing blocks, no data leaves successfully. The scores
are computed locally either way, and the lock/verify split is unchanged when
tracking is fully configured: the manifest never depends on where scores are
displayed.

The metric here is judge-free (`Equals`) so the demo is deterministic and the
only thing under discussion is the bar. With an LLM judge the lock matters
*more*, not less: the judge's identity belongs in `metric_args` and the
threshold still has to predate the scores.
