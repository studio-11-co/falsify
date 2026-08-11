# RewardHackingAgents × PRML — the commitment half of evaluator locking

[RewardHackingAgents](https://arxiv.org/abs/2603.11337) (Atinafu & Cohen)
measures evaluator tampering in ML-engineering agents and shows that locking
the evaluator eliminates it — tampering attempts in ~50% of natural episodes,
zero under the lock, at a 25–31% median runtime overhead. That lock protects
the run, at runtime, from the agent.

This example adds the complementary layer: a **pre-commitment** over the
episode's success criterion itself (metric, comparator, threshold, dataset
hash, seed), sealed to a SHA-256 before the run. The runtime lock keeps the
agent from patching the grader; the commitment lets a **third party** verify,
long after the workspace is gone, that the bar was fixed in advance and never
quietly moved. Different threat, different clock: one secures the hour of the
experiment, the other the years after it.

## Run it

```bash
pip install falsify
python prml_map.py
```

Expected output:

```
[lock]   auc >= 0.70 sealed before the run   sha256 f6cc4a550869d240…
[A] observed auc = 0.74  -> PASS
[B] bar edited 0.70 -> 0.60 after the run    -> TAMPERED (hash mismatch)
demo OK
```

Fully offline: the dataset hash is computed over the synthetic
`credit_risk_split.csv` in this directory so the demo runs anywhere; in a
real episode you would hash the task's actual data split. Scenario numbers
are illustrative — this maps the *pattern*, it does not reproduce the
paper's experiments.

## What maps to what

| RewardHackingAgents concept | PRML field |
|---|---|
| Episode success criterion (e.g. `auc >= 0.70`) | `metric`, `comparator`, `threshold` |
| Task / variant / trust regime | `metric_args.rha_*` (context, carries no semantics) |
| Episode data split | `dataset.hash` (SHA-256 of the bytes) |
| Run seed | `seed` |
| Who makes the claim | `producer.id` |

Committing the manifest to the public registry
([registry.falsify.dev](https://registry.falsify.dev)) additionally
countersigns it with an independent RFC 3161 timestamp and mirrors it to a
transparency log — so "the bar predates the run" no longer rests on the
operator's word.

## Boundary

Per PRML §8.1: a commitment does not fix selective publication, dataset
contamination, or a grader that was wrong from the start. It proves the bar
was locked — never that the result is right.
