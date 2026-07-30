# lm-evaluation-harness + PRML — lock the bar before the run

[lm-evaluation-harness](https://github.com/EleutherAI/lm-evaluation-harness)
answers *"what score did the model get?"*. PRML answers a different question:
*"was the bar that score had to beat fixed before anyone saw the result?"*

This example locks a harness claim — metric, comparator, threshold, dataset
bytes, **task configuration**, seed, producer — to a SHA-256 before
`simple_evaluate` runs, then grades the observed score against the locked
manifest. Quietly softening the threshold (or swapping the prompt template)
after seeing a red result flips the verdict to `TAMPERED` instead of `PASS`.

## Run it (offline — no model download, no API key, no network)

```bash
pip install -r requirements.txt
python run_with_prml.py
```

Expected output (abbreviated):

```
[A] locked  exact_match >= 0.85   hash 594e92ab4ed16e29…
[A] observed exact_match = 0.90
[A] verdict: PASS

[B] locked  exact_match >= 0.95   hash c2af6435c0a6350e…
[B] observed exact_match = 0.90  (would FAIL the locked bar)
[B] verdict after softening the bar: TAMPERED

demo OK — A must PASS, B must read TAMPERED
```

Both scenarios drive the **real harness pipeline** (`lm_eval.simple_evaluate`
over a local task YAML, with a scripted `LM` subclass standing in for a model),
so what is exercised is the same task-loading, prompting and metric code a real
run uses. The scripted model answers 9/10 toy questions correctly, so
`exact_match` is a deterministic 0.90.

## What gets locked, in harness terms

| PRML field | Harness concept |
|---|---|
| `metric` | the task's `metric_list` entry (here `exact_match`) |
| `comparator`, `threshold` | the claim being made about the score — the harness itself has no opinion here; this is the part people edit after the fact |
| `dataset.hash` | SHA-256 of the dataset bytes (for Hub-hosted tasks: pin and hash the resolved revision) |
| `metric_args.lm_eval_task` | the task name |
| `metric_args.task_config_sha256` | SHA-256 of the task YAML — prompt template, split, generation settings and aggregation all move the score, so "same task" becomes checkable |
| `seed` | the same value passed as `--seed` / `random_seed` |
| `producer.id` | who is making the claim (and for real runs, the model revision) |

## Files

- `prml_lm_eval.py` — the bridge: `lock_harness_claim()` before the run,
  `verify_observed()` after. Depends only on the `falsify` reference package
  (three pure functions; no CLI, no network, no account).
- `toy_task/prml_toy_qa.yaml` + `toy_task/toy_qa.jsonl` — a self-contained
  10-question generate-until task so the demo runs anywhere.
- `run_with_prml.py` — scenarios A (honest PASS) and B (softened bar →
  TAMPERED).

## What this does and does not prove

The locked hash proves the bar was fixed no later than the recorded moment and
has not moved since. It does **not** prove the evaluation ran after the lock,
that the metric implementation is sound, or that the result is representative —
see §8.1 of the [PRML spec](https://spec.falsify.dev/v0.1) for the full
boundary. Committing the hash to the public registry
([registry.falsify.dev](https://registry.falsify.dev)) adds an independent
RFC 3161 timestamp and a transparency-log entry on top.
