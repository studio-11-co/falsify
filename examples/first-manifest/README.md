# First manifest — a real, runnable PRML example

Everything here is real and committed. No placeholders, no API keys, no
network. Clone the repo, run the commands below, and you will get the exact
output shown — including the same lock hash, because the inputs are fixed.

## Files

- `eval_set.jsonl` — a tiny sentiment eval set (10 labelled rows).
- `run_eval.py` — computes accuracy on it. No dependencies.
- `accuracy.prml.yaml` — the PRML manifest. `dataset.hash` is the **real**
  SHA-256 of `eval_set.jsonl`, not a placeholder.

## Walkthrough

Install the CLI, then `cd` into this directory:

    pip install falsify
    cd examples/first-manifest

### 1. Lock the bar (before the run)

    falsify lock accuracy.prml.yaml

    locked: accuracy.prml.yaml
      canonical bytes: 316
      sha256:          9cb2a71b75355dd52d56ea79212a79442eec6ed512bc93c4bb25ff897c4b1005
      sidecar:         accuracy.prml.prml.sha256

The bar — accuracy ≥ 0.85 on this exact dataset — is now committed to a hash.

### 2. Run the eval, then verify

    python3 run_eval.py
    # 0.9000

    falsify verify accuracy.prml.yaml --observed 0.9
    echo "exit: $?"

    PASS  metric=accuracy  observed=0.9  >=  threshold=0.85
    exit: 0

`0.9 ≥ 0.85`, manifest untouched → `PASS` (exit 0).

### 3. The moved goalpost → TAMPERED

Now edit `accuracy.prml.yaml` after locking — say you scored lower and quietly
drop `threshold: 0.85` to `0.80`. The hash no longer matches:

    falsify verify accuracy.prml.yaml --observed 0.9
    echo "exit: $?"

    TAMPERED
      recorded:    9cb2a71b75355dd52d56ea79212a79442eec6ed512bc93c4bb25ff897c4b1005
      recomputed:  77559d468d45161d5194fe37deb20649de808c9440d20ba0c616cd2a1e851af9
    exit: 3

The bar moved, and it is self-evident from the manifest alone (exit 3).
Restore `threshold: 0.85` and verify is `PASS` again.

## Why this is real

`dataset.hash` is `shasum -a 256 eval_set.jsonl`. `run_eval.py` reads that same
file. So the observed value, the dataset commitment, and the lock hash are all
reproducible by anyone — which is the whole point: the claim is checkable, not
taken on trust.
