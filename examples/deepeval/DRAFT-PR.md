# Draft PR — `deepeval`: optional PRML pre-registration for metric thresholds

> Target repo: [`confident-ai/deepeval`](https://github.com/confident-ai/deepeval)
> Status: **draft for discussion** — open an issue first per their CONTRIBUTING.
> This file is the proposal we would submit; the runnable proof is the sibling
> example in this directory (`run_with_prml.py`, verified output in `README.md`).

---

## Title

`feat(integrations): optional PRML pre-registration for metric thresholds`

## Summary

Add an **opt-in** integration that lets a DeepEval user lock a metric's bar —
`metric`, `comparator`, `threshold`, the dataset bytes, `seed`, `producer` — to
a SHA-256 **before** an evaluation runs, and verify the observed score against
that locked bar afterwards. If the threshold (or any bound field) is changed
between lock and verify, verification returns `TAMPERED` instead of `PASS`.

No core changes. New code lives under `deepeval/integrations/prml.py` behind an
optional extra. If the extra isn't installed, nothing changes.

## Motivation

Every DeepEval metric exposes a `threshold`, and `is_successful()` is
`score >= threshold`. That threshold is the single most gameable knob in an eval
suite: a run fails at `0.95`, someone lowers it to `0.85`, CI goes green, and no
artifact records that the bar moved *after* the result was seen. DeepEval can't
distinguish a pre-committed bar from a retro-fitted one, because nothing commits
the bar before the run.

PRML (Pre-Registered ML Manifest) is a tiny open spec that does exactly that
commitment: it hashes the bar to SHA-256 before the run, so moving it later is
detectable from the manifest alone — offline, by anyone, no account or server.

## What this adds

```
deepeval/
  integrations/
    prml.py            # lock_metric() / verify_observed() — ~60 lines, pure functions
docs/.../integrations-prml.mdx   # one page: when to use it, the gamed-threshold case
pyproject.toml         # optional extra:  deepeval[prml] -> falsify
tests/integrations/test_prml.py  # the offline PASS + TAMPERED case (no LLM, no key)
```

Public surface (stable, three calls):

```python
from deepeval.integrations.prml import lock_metric, verify_observed

lock = lock_metric(metric, claim_id=..., metric_id="accuracy", created_at=...,
                   dataset_path=..., dataset_id=..., seed=42, producer_id=...)  # BEFORE run
observed = evaluate(...)               # DeepEval, unchanged
verdict  = verify_observed(lock, observed)   # "PASS" | "FAIL" | "TAMPERED"
```

The implementation is the `prml_deepeval.py` in this directory, upstreamed
verbatim. It depends only on the PRML reference package `falsify` (three pure
functions: `validate_manifest`, `manifest_hash`, `evaluate_predicate`) — no CLI,
no network.

## Why it's safe to merge

- **Additive and opt-in.** Zero changes to DeepEval's core or existing metrics;
  gated behind the `deepeval[prml]` extra.
- **No lock-in.** The PRML spec is under the Community Specification License 1.0 and the reference implementations
  are MIT, across four languages. Conformance is defined by published byte-level
  test vectors, not a vendor binary. DeepEval (and its users) can re-implement
  or drop it at any time with no dependency on us.
- **Honest scope.** PRML proves the *bar was locked*, not that the *score is
  correct* or that every claim was published. The docs page says so plainly and
  points to the spec's §8.1 threat model for what still needs an execution
  attestation and a publication anchor.

## Test plan

`tests/integrations/test_prml.py` runs the offline example in this directory:
a 10-row exact-match set (accuracy `0.90`), asserting `PASS` against a locked
`>= 0.85` bar and `TAMPERED` when a locked `>= 0.95` bar is lowered to `0.85`
post-hoc. Deterministic, no LLM, no API key — the locked digests
(`8df76209…`, `056e32e9…`) reproduce on any machine.

## Notes for maintainers

We're the PRML authors and happy to own this integration's maintenance and keep
it green against DeepEval releases. We opened this as a draft to get your read on
*shape* before investing in the docs page and the optional-extra wiring — if
you'd rather it live as a community package (`deepeval-prml`) than in-tree,
that's completely fine; tell us which you prefer.

Contact: `hello@falsify.dev` · spec: https://spec.falsify.dev/v0.1
