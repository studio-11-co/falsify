# Examples — what else can you falsify?

Each example has: the claim in plain English, the falsification
criterion, a `spec.yaml` sketch, and what PASS / FAIL would mean.
These are illustrative — drop them into `.falsify/<name>/spec.yaml`
and adapt the `experiment.command` to your codebase.

## Example 1 — Model accuracy regression

> Scaffold this with `falsify-engine init --template accuracy`.

Claim (plain): *"Our classifier maintains at least 92% accuracy on
the holdout set."*

Spec sketch:

    claim: Classifier accuracy ≥ 92% on holdout.
    falsification:
      failure_criteria:
        metric: accuracy
        direction: below
        threshold: 0.92
      minimum_sample_size: 500
      stopping_rule: fixed sample
    experiment:
      command: python3 eval.py --holdout data/holdout.csv --report out.json
      dataset: data/holdout.csv
      metric_fn: eval:accuracy

Run `falsify why <name>` for a plain-English explanation of the
current state. Behavior:

- PASS (exit 0): accuracy ≥ 0.92 on ≥ 500 rows.
- FAIL (exit 10): accuracy < 0.92.
- INCONCLUSIVE (exit 2): fewer than 500 rows evaluated.

## Example 2 — Latency regression gate

> Scaffold this with `falsify-engine init --template latency`.

Claim: *"P95 request latency stays under 200ms after this
refactor."*

Spec sketch:

    claim: P95 latency ≤ 200ms on staging benchmark.
    falsification:
      failure_criteria:
        metric: p95_latency_ms
        direction: above
        threshold: 200
      minimum_sample_size: 10000
      stopping_rule: fixed sample
    experiment:
      command: python3 bench/run.py --n 10000 --out bench.json
      metric_fn: bench:p95_ms

Run `falsify why <name>` for a plain-English explanation of the
current state. Behavior: PASS = latency stays within the budget; FAIL = a
regression merged in. Useful as a pre-release gate — CI blocks
the release tag when `falsify-engine verdict` exits 10.

## Example 3 — Prediction market calibration

> Scaffold this with `falsify-engine init --template brier`.

Claim: *"Our market prices are well-calibrated: Brier score below
0.25 across last-30-day closed markets."*

Spec sketch:

    claim: Brier score < 0.25 on closed markets, last 30 days.
    falsification:
      failure_criteria:
        metric: brier
        direction: above
        threshold: 0.25
      minimum_sample_size: 20
      stopping_rule: fixed sample (30-day rolling window)
    experiment:
      command: python3 calibration/brier.py --window 30d --out out.json
      metric_fn: calibration.brier:compute

Run `falsify why <name>` for a plain-English explanation of the
current state. Behavior: this is exactly the calibration sample in
`examples/calibration_sample/` — the generalization. PASS = calibrated,
FAIL = re-train or re-price.

## Example 4 — Code review LLM agreement

> Scaffold this with `falsify-engine init --template llm-judge`.

Claim: *"When our LLM code reviewer flags a line as critical, a
human reviewer agrees at least 80% of the time."*

Spec sketch:

    claim: Human-LLM agreement on critical-line flags ≥ 80%.
    falsification:
      failure_criteria:
        metric: agreement_rate
        direction: below
        threshold: 0.80
      minimum_sample_size: 100
      stopping_rule: fixed sample
    experiment:
      command: python3 eval_agreement.py --labeled labeled.csv --predictions preds.csv --out out.json
      metric_fn: eval_agreement:agreement_rate

Run `falsify why <name>` for a plain-English explanation of the
current state. Behavior: FAIL = the LLM reviewer is disagreeing with humans too
often → don't ship it as the default path. PASS = safe to enable
without human-in-the-loop for every flag.

## Example 5 — AB test preregistration (bonus)

> Scaffold this with `falsify-engine init --template ab`.

Claim: *"Variant B has higher click-through rate than A, at p<0.05
with a minimum detectable effect of 2 percentage points."*

Spec sketch:

    claim: Variant B CTR > Variant A CTR (MDE 2pp, alpha 0.05).
    falsification:
      failure_criteria:
        metric: ctr_b_minus_a
        direction: below
        threshold: 0.02
      minimum_sample_size: 20000
      stopping_rule: fixed sample (no peeking)
    experiment:
      command: python3 ab/run.py --snapshot out.json
      metric_fn: ab:lift

Run `falsify why <name>` for a plain-English explanation of the
current state. Behavior: the `stopping_rule: fixed sample (no peeking)` note
guards against p-hacking via repeated looks. FAIL = no detectable
lift; PASS = lift ≥ 2pp on the full pre-registered sample.

## Why the template is the same

All five examples share the same schema: metric + direction +
threshold + minimum_sample_size + stopping_rule. This uniformity
is the point — every empirical claim in your stack becomes a
hash-anchored, CI-gated artifact, regardless of domain.

## Adapting an example to your repo

1. Copy the spec sketch into `.falsify/<name>/spec.yaml`.
2. Fill in `experiment.command` to run your evaluation.
3. Point `metric_fn` at the `module:function` that reads the
   experiment output and returns a `(float, int)` tuple where the
   float is the metric and the int is the sample size.
4. Run the pipeline:

       python3 falsify.py lock <name>
       python3 falsify.py run <name>
       python3 falsify.py verdict <name>

5. If this check belongs in your release flow, install the hook so
   CI enforces it automatically:

       python3 falsify.py hook install

## Sharing a claim with a peer

When you want a reviewer, regulator, or collaborator to verify your
verdicts from scratch, export the audit trail and ship them the
JSONL plus the original `spec.yaml`:

    python3 falsify.py export --include-runs > audit.jsonl

The file has one JSON object per event — every lock, every run,
every verdict — each with a `schema_version`, a timestamp, and
(for verdict records) a `locked_hash` that chains back to the
original lock. Two invocations against the same `.falsify/`
produce byte-identical output, so the peer can re-run `export`
after re-running your experiment and diff the two files to confirm
the audit chain matches.

On the receiving end:

    # peer just received audit.jsonl
    python3 falsify.py verify audit.jsonl   # exit 0 if trustworthy

`verify` walks the JSONL, confirms each verdict's `locked_hash`
resolves to a preceding lock's `canonical_hash`, checks timestamps
are monotonic per spec, and refuses any file that was reordered
or whose hash chain broke after export (exit 10).
