# Scoring Published ML Claims Against PRML v0.1

**A methodology for retroactive conformance assessment.**

**Editor:** Cüneyt Öztürk — `hello@falsify.dev`
**Date:** 2026-05-01
**Spec under analysis:** [PRML v0.1](https://spec.falsify.dev/v0.1)
**License:** CC BY 4.0

---

## 0. Why score?

The first question every reviewer of PRML asks is: **how many published ML claims would pass the spec today, retroactively?** The answer matters because it sets the calibration:

- If 90% of papers would already pass, PRML is redundant.
- If <10% would pass, PRML is solving a real problem.

This document defines a five-dimension rubric for scoring any published ML accuracy claim against PRML v0.1 conformance, applies it to **12 synthetic but reporting-pattern-faithful examples** drawn from common ML publication practice, and outlines how the methodology extends to a 100-paper mass analysis.

This is **not** an indictment of any specific researcher or paper. The synthetic examples reflect *aggregate* publication norms across NeurIPS / ICLR / ACL / CVPR proceedings 2020-2025. Real-paper analysis using this rubric is a separate, careful exercise that follows.

---

## 1. The rubric (5 dimensions, 0-2 points each, 10-point scale)

A published claim is scored on five binary-or-partial criteria. Each dimension maps directly to a PRML v0.1 required field (§2.1 of the spec).

### 1.1 Metric precision (PRML field: `metric`)

| Score | Criterion |
|---|---|
| **0** | Vague or composite metric mentioned without exact definition. ("achieves human-level performance", "outperforms prior work") |
| **1** | Named metric (`accuracy`, `f1`, `auroc`) but variant unspecified (e.g., `f1` without micro/macro distinction; `accuracy` on top-k unspecified) |
| **2** | Named metric with full disambiguation: micro-F1 vs macro-F1, top-1 vs top-5, EM vs F1 for QA, mean-of-N seeds vs single run |

### 1.2 Threshold pre-registration (PRML field: `comparator` + `threshold`)

| Score | Criterion |
|---|---|
| **0** | No threshold; reported as a single point estimate ("our method achieves 91.3%") |
| **1** | Threshold mentioned in narrative ("we target 90%") but no pre-registration timestamp |
| **2** | Threshold committed to a public artifact (preprint, technical report, dated registry) **before** the experiment was run |

### 1.3 Dataset binding (PRML field: `dataset.id` + `dataset.hash`)

| Score | Criterion |
|---|---|
| **0** | Dataset named only by category ("ImageNet", "GLUE") with no version or slice information |
| **1** | Specific version and split named ("ImageNet val 2012", "GLUE MRPC dev") but no content hash; reproducibility depends on dataset host integrity |
| **2** | Specific version + content hash (SHA-256 or equivalent) committed to a public artifact, allowing byte-exact verification years later |

### 1.4 Seed reporting (PRML field: `seed`)

| Score | Criterion |
|---|---|
| **0** | No seed reported. Single run; no information about variance |
| **1** | Seed reported OR mean ± stdev across N runs reported (with N stated) |
| **2** | Seed reported AND multi-run distribution reported AND seed selection methodology disclosed (e.g., "seeds 0..9 from numpy.random.SeedSequence default") |

### 1.5 Hash / commitment integrity (PRML field: full manifest binding)

| Score | Criterion |
|---|---|
| **0** | No cryptographic record of the claim. Authors could (in principle) have edited the threshold post-hoc; a reader cannot detect this |
| **1** | Code commit hash reported in paper. Lets reader replay code; does not prevent post-hoc edits to numerical claims unless those are also hash-bound |
| **2** | Full PRML manifest (or equivalent: dated preregistration ID + claim hash) published before experiment ran |

### 1.6 Aggregate score

- **0-3:** Non-conformant. Claim is unfalsifiable in practice.
- **4-6:** Partially conformant. Some integrity floor; gaps in pre-experimental commitment.
- **7-9:** Mostly conformant. Practical equivalent to PRML modulo formal binding.
- **10:** Fully conformant. Indistinguishable from a PRML-bound claim.

---

## 2. Twelve worked examples (synthetic, pattern-faithful)

Each example is **synthetic** — not a real published paper — but constructed to reflect the dominant reporting style of a recognizable subfield. Citations are intentionally generic to avoid implying false claims about real authors.

### Example 1 — Vision classifier on ImageNet (typical 2021-vintage)

> *"We achieve 87.4% top-1 accuracy on ImageNet validation, surpassing prior work by 1.2 points."*

| Dimension | Score | Reasoning |
|---|---|---|
| Metric | 1 | top-1 specified; variance disclosure absent |
| Threshold | 0 | No threshold; point estimate only |
| Dataset | 1 | ImageNet val implied; no hash |
| Seed | 0 | Single run; no seed |
| Hash binding | 1 | Code released on GitHub with commit hash |
| **Total** | **3 / 10** | Non-conformant |

### Example 2 — NLP benchmark with multi-seed reporting

> *"Our model reaches 89.2 ± 0.4 macro-F1 on GLUE-MRPC across 5 random seeds (0-4)."*

| Dimension | Score | Reasoning |
|---|---|---|
| Metric | 2 | macro-F1 explicit |
| Threshold | 0 | Point estimate |
| Dataset | 1 | GLUE-MRPC named; no hash |
| Seed | 2 | Seeds disclosed, distribution reported |
| Hash binding | 1 | Commit hash on Papers With Code |
| **Total** | **6 / 10** | Partially conformant |

### Example 3 — Code generation (HumanEval-style)

> *"Pass@1 = 67% on HumanEval at temperature 0.0."*

| Dimension | Score | Reasoning |
|---|---|---|
| Metric | 2 | pass@1 + temperature disambiguated |
| Threshold | 0 | No pre-registration |
| Dataset | 1 | HumanEval canonical; no hash |
| Seed | 1 | Temperature 0 → deterministic; explicit |
| Hash binding | 0 | Internal model; no public commit |
| **Total** | **4 / 10** | Partially conformant |

### Example 4 — Reinforcement-learning agent

> *"Mean episodic return of 1247 ± 89 on Atari Breakout over 100 seeds."*

| Dimension | Score | Reasoning |
|---|---|---|
| Metric | 1 | Mean return; episode-length conventions unstated |
| Threshold | 0 | Point estimate |
| Dataset | 1 | Breakout v4 implied |
| Seed | 2 | 100-seed distribution reported |
| Hash binding | 1 | Code + checkpoint released |
| **Total** | **5 / 10** | Partially conformant |

### Example 5 — RAG evaluation (recent)

> *"Retrieval-augmented model scores 73.4 EM on Natural Questions."*

| Dimension | Score | Reasoning |
|---|---|---|
| Metric | 2 | EM (exact match) standard |
| Threshold | 0 | Point estimate |
| Dataset | 1 | NQ named; no hash |
| Seed | 0 | Retrieval is non-deterministic at inference; not addressed |
| Hash binding | 0 | Internal infrastructure |
| **Total** | **3 / 10** | Non-conformant |

### Example 6 — Medical imaging (high-stakes)

> *"AUROC = 0.94 (95% CI 0.91-0.97) for pneumonia detection on chest X-rays."*

| Dimension | Score | Reasoning |
|---|---|---|
| Metric | 2 | AUROC + CI |
| Threshold | 1 | Pre-specified clinical target ("≥ 0.85") in trial registry |
| Dataset | 1 | Specific hospital cohort; not byte-hashed |
| Seed | 1 | CI implies multiple runs; methodology unstated |
| Hash binding | 1 | Trial registered on ClinicalTrials.gov before experiment |
| **Total** | **6 / 10** | Partially conformant — the *only* example here that pre-registered a threshold, because clinical trials require it |

### Example 7 — LLM reasoning benchmark

> *"GPT-X achieves 92.7% on MMLU."*

| Dimension | Score | Reasoning |
|---|---|---|
| Metric | 1 | Accuracy on multi-task; no per-subtask breakdown |
| Threshold | 0 | Point estimate |
| Dataset | 1 | MMLU canonical; version unspecified |
| Seed | 0 | Single decoding pass; no seed |
| Hash binding | 0 | Closed model |
| **Total** | **2 / 10** | Non-conformant |

### Example 8 — Speech recognition WER

> *"5.2% word error rate on LibriSpeech test-clean."*

| Dimension | Score | Reasoning |
|---|---|---|
| Metric | 2 | WER, named split |
| Threshold | 0 | Point estimate |
| Dataset | 1 | test-clean canonical; no hash |
| Seed | 0 | No seed |
| Hash binding | 1 | Model released |
| **Total** | **4 / 10** | Partially conformant |

### Example 9 — Tabular data competition winner

> *"Won Kaggle competition X with 0.847 ROC-AUC on private leaderboard."*

| Dimension | Score | Reasoning |
|---|---|---|
| Metric | 2 | ROC-AUC standard |
| Threshold | 0 | No threshold (competition is ordinal) |
| Dataset | 2 | Kaggle holds the dataset hash; competition format guarantees byte integrity |
| Seed | 1 | Submission seed known to organizer |
| Hash binding | 2 | Kaggle's audit trail is effectively a content-addressed registry |
| **Total** | **7 / 10** | Mostly conformant — competitions get this right by accident |

### Example 10 — Self-supervised pretraining ablation

> *"Removing component A reduces downstream accuracy by 2.4 points."*

| Dimension | Score | Reasoning |
|---|---|---|
| Metric | 1 | Accuracy delta; baseline conditions partial |
| Threshold | 0 | No commitment |
| Dataset | 1 | Downstream tasks named; not hashed |
| Seed | 0 | Single ablation run typical |
| Hash binding | 0 | Internal infrastructure |
| **Total** | **2 / 10** | Non-conformant |

### Example 11 — Multi-modal benchmark

> *"VQA accuracy of 81.5% on VQAv2 test-dev."*

| Dimension | Score | Reasoning |
|---|---|---|
| Metric | 1 | "VQA accuracy" non-standard formula understood by community but unstated |
| Threshold | 0 | Point estimate |
| Dataset | 1 | VQAv2 test-dev named |
| Seed | 0 | Server-side eval; methodology opaque |
| Hash binding | 0 | Eval harness closed |
| **Total** | **2 / 10** | Non-conformant |

### Example 12 — Pre-registered NeurIPS reproducibility-track submission

> *"As pre-registered on OSF (osf.io/abc123, 2024-09-12), our method achieves accuracy ≥ 85% on dataset D, hash sha256:e3b0…b855, seed 42."*

| Dimension | Score | Reasoning |
|---|---|---|
| Metric | 2 | Accuracy specified |
| Threshold | 2 | Pre-registered with timestamp |
| Dataset | 2 | Hash committed |
| Seed | 2 | Disclosed |
| Hash binding | 2 | OSF pre-registration is timestamped + hash-committed |
| **Total** | **10 / 10** | Fully conformant — equivalent to a PRML manifest in all but format |

---

## 3. Aggregate findings on this 12-example synthetic sample

| Score band | Count | Percent |
|---|---|---|
| 0-3 (non-conformant) | 5 | 42% |
| 4-6 (partially conformant) | 5 | 42% |
| 7-9 (mostly conformant) | 1 | 8% |
| 10 (fully conformant) | 1 | 8% |

**Mean score:** 4.5 / 10

**Median:** 4 / 10

**Reading:** even on a sample deliberately chosen to span best- and worst-case publication practices, only **8% reach full PRML conformance**. The dominant failure mode is **threshold non-pre-registration** (Dimension 1.2 averaged 0.25 / 2 across the sample) — not because authors are dishonest, but because no infrastructure existed to commit a threshold before the experiment ran.

PRML changes that infrastructure cost from "fork OSF + write a 200-word pre-registration" to "run `falsify lock`."

---

## 4. Methodology for extending to 100 real papers

### 4.1 Sampling

- 100 papers, balanced across NeurIPS 2024-2026, ICLR 2025-2026, ACL 2024-2026, and CVPR 2024-2026 main tracks.
- Stratified by venue and year (25 per venue × 4 venues, or 33 per year × 3 years).
- Random selection within each stratum from accepted-papers list.

### 4.2 Scoring

- Two independent raters apply the rubric to each paper.
- Disagreements > 1 point per dimension trigger a third rater + discussion.
- Final score = median of 2-3 raters per dimension.

### 4.3 Pre-registration

The mass analysis itself is to be pre-registered using PRML, with:
- `metric: scoring_rubric_v0.1`
- `threshold` for headline claim ("at most X% of papers reach 7+/10")
- Dataset hash = SHA-256 of the paper-list CSV
- Seed for any RNG used in sample selection

If the analysis pre-registers a hypothesis ("≤ 15% of recent ML papers reach PRML 7+/10") and finds otherwise, the chain hash is the audit log. Self-application of the spec to the spec's own validation effort is the strongest possible demonstration.

### 4.4 Open-source the rubric, open-source the data

- All paper IDs, scores per dimension, and rater identities (with consent) released under CC BY 4.0.
- A community-maintained continuous-update version of the analysis *(consolidated into `spec.falsify.dev/analysis`, this directory; the separate `analysis.falsify.dev` subdomain was never provisioned; noted 2026-07-11)*.

---

## 5. Limitations

1. **Synthetic sample bias.** The 12 examples in §2 are the editor's construction; real-paper distribution may differ.
2. **Reporting style ≠ practice.** A paper that scores 2/10 on PRML conformance may still represent honest, reproducible work — the authors simply didn't publish the artifacts that PRML demands.
3. **Dimensional weighting.** All five dimensions are weighted equally; in practice, dimension 1.2 (threshold pre-registration) is the most decisive. A weighted variant is straightforward.
4. **Survivorship bias in published work.** Papers that *failed* their evaluations are typically not published. The score distribution among *published* papers is a ceiling on the practice; the distribution among *all run* experiments is worse.

---

## 6. Editor's position

The honest call is in two parts:

1. The synthetic 8% full-conformance rate is *roughly* what mass analysis of real papers will show. Any deviation > ±10 percentage points would surprise me.
2. The point of this exercise is **not** to embarrass any individual paper or author. The point is to show that the existing reporting infrastructure makes PRML adoption frictionless: most published work already produces 4-6 of the 10 points implicitly. Closing the remaining 4-6 costs one hash function call.

The 12-example exercise is reproducible: change any score, recompute the aggregate, file a pull request. The whole thing is a markdown table.

---

*Document drafted 2026-05-01 by Cüneyt Öztürk. Public review via GitHub Discussions on `studio-11-co/falsify`. CC BY 4.0.*
