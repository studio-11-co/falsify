# Worked Example — Pre-registering a HumanEval `pass@1` claim with PRML

**Status:** procedure-and-output walkthrough. The script is real and runnable, but the model, the `pass@1` figure, and the hashes shown below are **illustrative** — running it for real needs your own API credentials. For a fully committed, self-contained example you can reproduce byte-for-byte with no API keys (real dataset hash, real lock hash, real PASS/TAMPERED), see [`examples/first-manifest/`](../first-manifest/).

**Goal:** demonstrate that PRML works on a real benchmark with a real model — not just on synthetic test vectors. Produce a manifest that can be independently verified by anyone with the dataset, the model checkpoint, and a SHA-256 implementation.

---

## What this walkthrough proves

By the end:

- A locked manifest binds the claim *"our model achieves pass@1 ≥ 0.65 on HumanEval"* to a SHA-256 digest **before** evaluation runs.
- The evaluation runs against the locked claim; the verifier emits a deterministic verdict.
- A subsequent reader can recompute the SHA-256, run their own evaluation against the same dataset and model, and obtain the same verdict — without trusting the producer.
- A tampered manifest (e.g. dropping the threshold to 0.50) is caught by the verifier with exit code 3 (TAMPERED).

---

## Procedure

### Step 1 — Pin the dataset

HumanEval is a 164-problem code-generation benchmark from OpenAI, hosted at <https://github.com/openai/human-eval>.

Pin a specific commit so the dataset bytes are reproducible:

```bash
git clone https://github.com/openai/human-eval
cd human-eval
git checkout 312c5e5cc934adb96c5c46f5b9f0e0df0091dcdb  # commit on 2023-08-22
sha256sum data/HumanEval.jsonl.gz
```

Expected output (the actual SHA-256 of the gzipped HumanEval data at that commit):

```
3dad34ddca7e76e0c6486717e1ab6707e10c4b2e5e7f1d44f6ca47a8e5e6c1e0  data/HumanEval.jsonl.gz
```

(In a real run, the SHA-256 here will be the real digest of the file at that commit. We use the placeholder above as an illustrative form.)

### Step 2 — Pick a model

For this walkthrough we use a hypothetical model `claude-opus-4-7` accessed via API. The model identifier and a checkpoint hash are recorded in the manifest so the verifier can confirm it ran against the right artifact.

If using OpenAI / Anthropic / other API: the "checkpoint hash" is the model identifier string itself, recorded in `model.id`. Set `model.hash` to the SHA-256 of a model fingerprint document if available, otherwise omit (`model.hash` is optional in v0.1).

If using a local checkpoint (e.g. Llama, Mistral): compute SHA-256 of the model weights file and record in `model.hash`.

### Step 3 — Author the spec, before running anything

```bash
falsify init humaneval_pass1_v1
```

Edit `.falsify/humaneval_pass1_v1/spec.yaml`:

```yaml
version: "prml/0.1"
claim_id: "01900000-0000-7000-8000-1eaf1eaf1eaf"
created_at: "2026-05-01T20:00:00Z"
metric: "pass@1"
comparator: ">="
threshold: 0.65
dataset:
  id: "humaneval"
  hash: "3dad34ddca7e76e0c6486717e1ab6707e10c4b2e5e7f1d44f6ca47a8e5e6c1e0"
  uri: "https://github.com/openai/human-eval/tree/312c5e5cc934adb96c5c46f5b9f0e0df0091dcdb"
model:
  id: "claude-opus-4-7"
  uri: "https://anthropic.com/news/claude-opus-4-7"
seed: 314159
producer:
  id: "falsify.dev"
notes: "Pre-registered before any evaluation run. Threshold of 0.65 chosen as the deployment target for the tier-2 code review system."
```

### Step 4 — Lock

```bash
$ falsify lock humaneval_pass1_v1
locked: yes (sha256:7f3c8a9d2b4e, locked_at 2026-05-01T20:00:15Z)
```

The hash `7f3c8a9d2b4e...` is now **the identity of this claim**. Any byte-level edit to the manifest produces a different identity.

### Step 5 — Run the evaluation

This is the part where actual inference happens. The walkthrough script is at [`run_humaneval.py`](run_humaneval.py) (in this directory) — it reads the locked spec, runs the eval, captures `pass@1`.

For the real run, you need API credentials configured in your environment. The walkthrough's purpose is to show the *flow*, not to consume API budget — feel free to substitute a smaller / cheaper / local model. The procedure is identical.

```bash
$ python3 run_humaneval.py humaneval_pass1_v1
loading dataset: humaneval (3dad34ddca7e76e0c... ✓ byte match)
loading model: claude-opus-4-7
generating 164 completions at temperature=0.0, seed=314159
[..............................................................]  164/164
scoring: 113 / 164 = 0.689
observed pass@1 = 0.689
wrote .falsify/humaneval_pass1_v1/run.json
```

### Step 6 — Verify

```bash
$ falsify verify humaneval_pass1_v1 --observed 0.689
PASS  metric=pass@1  observed=0.689  >=  threshold=0.65
exit 0
```

The claim is verified. A reader with the manifest, the dataset commit, and a model name can now reproduce this in their own environment.

### Step 7 — Demonstrate tamper detection

To prove the verifier catches post-hoc edits, modify the locked spec by hand (do not re-lock):

```bash
$ vim .falsify/humaneval_pass1_v1/spec.yaml
# (silently edit threshold from 0.65 to 0.50)
$ falsify verify humaneval_pass1_v1 --observed 0.689
TAMPERED  spec hash drift detected
recorded:    7f3c8a9d2b4e...
recomputed:  c9b1a234e567...
exit 3
```

The verifier refuses to emit a verdict on a tampered manifest. CI fails. The deploy does not happen.

---

## What the verifier needs from a third party

Anyone, with no access to your CI or your team, can verify this claim:

1. The manifest URL: `https://example.com/manifests/humaneval_pass1_v1.prml.yaml`
2. The sidecar URL: same path with `.prml.sha256` extension
3. The dataset (HumanEval at the pinned commit, public)
4. API access to the named model (or a local copy)
5. A SHA-256 implementation (every standard library)
6. Any PRML verifier (Python, Node.js, or Go reference impl, all open source)

The verifier:

```bash
$ wget https://example.com/manifests/humaneval_pass1_v1.prml.yaml
$ wget https://example.com/manifests/humaneval_pass1_v1.prml.sha256

# Recompute hash from received bytes
$ falsify hash humaneval_pass1_v1.prml.yaml
7f3c8a9d2b4e5c6f...

# Compare against sidecar
$ cat humaneval_pass1_v1.prml.sha256
7f3c8a9d2b4e5c6f...
# Match → manifest is untampered

# Run their own evaluation
$ python3 their_humaneval_runner.py --dataset HumanEval.jsonl.gz --model claude-opus-4-7 --seed 314159
observed pass@1 = 0.687  # might differ slightly due to API non-determinism

# Verify
$ falsify verify humaneval_pass1_v1.prml.yaml --observed 0.687
PASS  metric=pass@1  observed=0.687  >=  threshold=0.65
```

The third party has now independently verified the claim. They did not have to trust the producer at any point. The arithmetic is the audit.

---

## Failure modes the manifest prevents

Without PRML, the producer could quietly do any of the following, all of which inflate the published number without leaving a forensic trace:

| Attack | What the producer does | What PRML detects |
|---|---|---|
| Threshold drift | Run the eval, see 0.61, lower the threshold to 0.60, publish "≥ 0.60" | Hash drift if the threshold was ever locked at 0.65 |
| Slice selection | Run on all 164 problems, see 0.58, drop "the 12 that were known to be ambiguous", report 0.71 on the remaining 152 | Hash drift if `dataset.hash` was bound to the full 164-problem file |
| Silent re-runs | Run with seed 1 → 0.62, seed 2 → 0.59, seed 3 → 0.71, publish "0.71 with seed 3" | Hash bound `seed: 314159` before any run; only that seed counts |
| Model swap | Lock claim with `claude-opus-4-7`, publish results from a different (better) model checkpoint | Hash bound `model.id`; verifier refuses if a different model is presented |

Each row is a real observed failure mode in published ML accuracy claims. PRML eliminates them at the manifest layer, with no infrastructure beyond SHA-256 and the manifest format itself.

---

## A note on API non-determinism

The HumanEval `pass@1` metric is sensitive to:

- Decoding temperature (recorded in the eval script, NOT the manifest itself)
- Model checkpoint version drift (the API provider may silently update the model)
- Tokenizer differences between provider and reference

In v0.1, the manifest binds the *commitment* (metric, threshold, dataset, seed, producer). It does not bind the runtime decoding parameters. Two verifiers running the same manifest may observe slightly different `pass@1` values; the verdict (PASS / FAIL) should be robust within reasonable tolerances.

In v0.2 (target 2026-06-15) we add a `tolerance` field for precisely this — the verifier evaluates `|observed - threshold| ≤ tolerance` rather than bit-exact compare, accommodating API-side non-determinism while preserving the cryptographic commitment to the threshold itself.

For now, in v0.1, treat marginal gaps (e.g. observed 0.649 against threshold 0.65) as FAIL and re-run. PRML does not paper over numerical gaps; that is the spec's design choice, not an oversight.

---

## What this walkthrough does NOT do

- It does not download HumanEval and run it for you. The script is real but you supply API credentials.
- It does not make a claim about which model is best on HumanEval. The 0.689 figure is illustrative.
- It does not establish a publication-grade benchmark. PRML is the integrity floor; benchmark validity (which problems, which scoring, which sandbox) lives in HumanEval itself.

---

## Try it on your own benchmark

The flow generalises:

1. Pin the dataset (commit hash + SHA-256 of the data file).
2. Pin the model (provider+ID, or local checkpoint hash).
3. Author the spec with metric, comparator, threshold, seed.
4. `falsify lock` → SHA-256 commitment.
5. Run the eval.
6. `falsify verify --observed <value>`.
7. Publish the manifest URL + sidecar SHA-256 wherever your model card or paper lives.

The cost is one hash per claim. The benefit is a record that survives any team turnover, vendor change, or audit demand.

---

*Walkthrough draft 2026-05-01. Suggestions, refinements, real-data-runs welcome via [GitHub Discussion #6](https://github.com/studio-11-co/falsify/discussions/6) or `hello@falsify.dev`.*
