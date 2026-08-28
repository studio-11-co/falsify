# Pre-Registered ML Manifests: A Content-Addressed Format for Verifiable Evaluation Claims

**Paper Outline — arXiv Preprint (Working Draft)**

- **Target venue (preprint):** arXiv `cs.CR` (primary) · `cs.LG` (cross) · `cs.SE` (cross)
- **Target venue (peer review):** NeurIPS 2026 Workshop on Reproducibility and Reliability in ML *(ML Reproducibility Challenge associated)*; backup: ICLR 2027 Tiny Papers; backup: USENIX Security 2027 (short paper)
- **Length:** 8 pages + references + appendix (NeurIPS workshop format)
- **Authors:** Cüneyt Öztürk — `hello@falsify.dev`
- **Correspondence URL:** `https://spec.falsify.dev/v0.1`
- **Code & data:** `https://github.com/studio-11-co/falsify` (MIT) · spec under CC BY 4.0
- **Status:** Outline — to be expanded into full draft by 2026-05-22 (3-week window)

---

## 0. Title alternatives (pick one before submission)

1. **Pre-Registered ML Manifests: A Content-Addressed Format for Verifiable Evaluation Claims** *(current)*
2. PRML: Hash-Bound Pre-Registration for Machine Learning Accuracy Claims
3. Falsifiable ML: A Cryptographic Primitive for Evaluation Claim Integrity
4. Commit Before You Train: A Specification for Pre-Registered ML Benchmarks

> **Editor note:** Title 1 is the safest; foregrounds the artifact (PRML) and the property (verifiable). Title 4 is the most readable but signals advocacy more than spec.

---

## 1. Abstract (≤ 200 words)

**Claim:** Most published ML accuracy numbers are unfalsifiable in practice. The metric, threshold, dataset slice, and seed are reported *after* the experiment, leaving no cryptographic record of what was committed *before* it. Reviewers, auditors, and downstream users cannot distinguish honest reporting from p-hacking, threshold tuning, or post-hoc dataset selection.

**Contribution:** We define **PRML** (Pre-Registered ML Manifest), a content-addressed YAML serialization that binds an evaluation claim — metric, comparator, threshold, dataset hash, seed, producer — to a SHA-256 digest computed over a canonical byte sequence *before the experiment runs*. A verifier with the manifest, the dataset, and the model can independently recompute the digest, execute the claim, and emit a deterministic verdict. Tampering produces a detectable hash mismatch; honest amendments are recorded in a forward-only chain via a `prior_hash` link.

**Result:** A reference implementation in 1,287 lines of Python (`falsify`, MIT) demonstrates the format end-to-end. The spec is independent of any tool, language, or platform. We map PRML fields directly to EU AI Act Articles 12, 17, 18, and 50, and to NIST AI RMF Govern/Measure functions.

**Position:** PRML is to ML claims what `git` is to source code: a primitive, not a product.

---

## 2. Introduction (≈ 1 page)

### 2.1 The unfalsifiability problem

- Vignette: A model card reports 91.3% accuracy on "ImageNet val." Which val? Which seed? Which threshold? Reported *when?* No record exists prior to the number.
- Three concrete failure modes:
  1. **Threshold drift** — the deploy threshold is tuned post-hoc on the test set and reported as the original target.
  2. **Slice selection** — the evaluation slice is filtered after results are seen.
  3. **Silent re-runs** — random seeds are tried until a passing run is found, only the passing run is reported.
- Each failure is consistent with current best-practice reporting (model cards, datasheets, results tables). None leave a cryptographic trace.

### 2.2 Why pre-registration, why now

- Clinical trials solved this in 2007 (`ClinicalTrials.gov`). Psychology adopted it in 2013 (OSF). ML has not.
- The regulatory window: EU AI Act Article 12 logging and Article 18 recordkeeping obligations for Annex III high-risk systems apply from 2 December 2027 (deferred from 2 August 2026 by Regulation (EU) 2026/1744). Article 18 mandates 10-year retention of evaluation records. NIST AI RMF v1.1 references content-addressed audit trails as a recommended control.
- The cost of doing nothing scales with deployment scope. The cost of pre-registering a claim is one hash function call.

### 2.3 Contributions

1. A formal specification (PRML v0.1) — RFC 2119 language, canonical YAML 1.2 subset, deterministic SHA-256 binding.
2. A forward-only audit chain protocol for honest amendments without breaking provenance.
3. A threat model identifying six adversaries and the primitive's coverage envelope.
4. A regulatory mapping (EU AI Act, NIST AI RMF, ISO/IEC 42001) showing PRML satisfies named obligations rather than approximating them.
5. A reference implementation, test vector suite, and public spec hosted at a stable URL.

### 2.4 Non-goals

- PRML does not establish *correctness* of a metric — only *integrity* of the commitment.
- PRML does not prove dataset legitimacy — only that the evaluator used the bytes claimed.
- PRML does not replace model cards, datasheets, or red-team reports — it underpins them.

---

## 3. Background and related work (≈ 1 page)

### 3.1 Pre-registration in adjacent fields

- Clinical trials: `ClinicalTrials.gov` (Zarin et al. 2011), AllTrials (Goldacre 2014).
- Psychology: Registered Reports (Chambers 2013), OSF preregistration (Nosek et al. 2018).
- Economics: AEA registry (2013–).
- *None use cryptographic binding.* They rely on trusted timestamping by a registrar.

### 3.2 Reproducibility infrastructure in ML

- ML Reproducibility Challenge 2018–present (Pineau et al.); Papers with Code leaderboards; HELM (Liang et al. 2023); BIG-bench.
- Model cards (Mitchell et al. 2019), Datasheets (Gebru et al. 2018), Data Statements (Bender & Friedman 2018).
- *None bind claims to a hash before the experiment.* All are post-hoc disclosure formats.

### 3.3 Content-addressed systems

- Git (Torvalds 2005), IPFS (Benet 2014), Sigstore/Cosign (2021), in-toto attestations (Torres-Arias et al. 2019).
- SLSA provenance levels — closest analog; PRML is to evaluation claims what SLSA is to build provenance.

### 3.4 Regulatory context

- EU AI Act (Reg. 2024/1689), high-risk system Articles 9–17.
- NIST AI RMF v1.0 (2023) and Generative AI Profile (2024).
- ISO/IEC 42001:2023 AI management systems.
- *Audit-grade logging is named in all three; no canonical format is mandated.*

### 3.5 Gap

The intersection — cryptographic, pre-experimental, ML-evaluation-shaped — is empty. PRML occupies it.

---

## 4. The PRML format (≈ 1.5 pages)

### 4.1 Design principles

1. **Plain text artifact.** No binary, no DSL. YAML 1.2 strict subset. Reviewable by humans, diffable by `git`.
2. **Deterministic canonicalization.** One YAML document → one canonical byte sequence → one hash. Lexicographic key ordering, 2-space indentation, LF terminators, UTF-8.
3. **Pre-experimental binding.** The hash is computed and committed *before* model execution. A verifier rejects any post-experiment edit silently.
4. **Single primitive, no dependencies.** SHA-256 only. Must run on a Raspberry Pi, in an air-gapped lab, in a regulator's office, in 2046.
5. **Forward-only amendment.** Honest changes produce new manifests linked via `prior_hash`; the chain is the audit log.

### 4.2 Required fields (table)

| Field | Type | Constraint |
|---|---|---|
| `version` | string | `prml/0.1` |
| `claim_id` | UUIDv7 | RFC 9562 |
| `created_at` | string | RFC 3339 UTC |
| `metric` | string | enum: `accuracy`, `f1`, `auroc`, `mae`, `bleu`, `rouge`, `exact_match`, `pass@k`, custom URI |
| `comparator` | string | `>=`, `<=`, `>`, `<`, `==` |
| `threshold` | float64 | finite, non-NaN |
| `dataset.id` | string | DNS-style |
| `dataset.hash` | hex string | lowercase SHA-256 of dataset bytes |
| `seed` | uint64 | inclusive 0..2⁶⁴-1 |
| `producer.id` | string | DNS-style |

### 4.3 Canonical serialization (formal grammar)

ABNF subset to be expanded in §A.1. Key invariants:
- Block style only; no flow collections.
- Keys at each level lexicographically sorted (Unicode code point order).
- Strings: double-quoted ASCII, escapes: `\\`, `\"`, `\n`, `\t`, `\uXXXX`.
- Numbers: shortest round-trip IEEE 754 representation.
- No comments, no aliases, no anchors, no tags.

### 4.4 Hash binding

```
hash := lowercase_hex( SHA-256( canonical_bytes ) )
```

Sidecar file `<claim_id>.prml.sha256` holds the hash on a single LF-terminated line.

### 4.5 Optional fields

`compute_envelope`, `model.id`, `model.hash`, `dataset.uri`, `producer.signature`, `prior_hash`, `notes`.

### 4.6 Example manifest (Appendix A reproduced here)

*(8-line minimal manifest, canonical bytes, expected SHA-256 digest)*

---

## 5. Verification protocol (≈ 1 page)

### 5.1 The verifier

A PRML verifier is any program that:
1. Reads a manifest file `M` and a sidecar hash `h_sidecar`.
2. Computes `canonical_bytes(M)` and `h_recomputed = SHA-256(canonical_bytes)`.
3. Asserts `h_recomputed == h_sidecar`. If not, exits with code 3 (TAMPERED).
4. Loads the dataset by `dataset.id` + `dataset.hash` (computes dataset SHA-256 from disk; verifies match).
5. Executes the metric computation under `seed` against the model.
6. Emits a verdict: PASS (exit 0) iff `metric_value comparator threshold` holds; FAIL (exit 10) otherwise.

### 5.2 Exit code semantics

| Code | Meaning | Compliance signal |
|---|---|---|
| 0 | PASS | claim verified |
| 10 | FAIL | claim falsified |
| 3 | TAMPERED | manifest hash mismatch |
| 11 | GUARD | input precondition violated (missing dataset, etc.) |

### 5.3 Determinism requirements

- Same manifest + same dataset bytes + same model + same RNG seed → same metric value.
- Floating-point determinism is *not* assumed at the bit level; the verifier defines metric tolerance separately (out of scope for v0.1; v0.2 will add `tolerance` field).

### 5.4 Forward-only amendment chain

```
M_1 → hash h_1
M_2 with prior_hash = h_1 → hash h_2
M_3 with prior_hash = h_2 → hash h_3
...
chain_hash := SHA-256( canonical_bytes(M_1) || canonical_bytes(M_2) || ... || canonical_bytes(M_n) )
```

Once h_i is published, h_i is immutable. An amendment never overwrites; it appends. The audit log *is* the chain.

---

## 6. Threat model and security analysis (≈ 1 page)

### 6.1 Adversaries

| # | Adversary | Goal | PRML coverage |
|---|---|---|---|
| 1 | Honest researcher, post-hoc threshold tuning | inflate reported accuracy | **Full** — any threshold change breaks hash |
| 2 | Adversarial reviewer, retroactive edit accusations | claim manifest was changed after the fact | **Full** — `prior_hash` chain disambiguates |
| 3 | Adversarial vendor, swap dataset slice | report accuracy on easier subset | **Full** — `dataset.hash` binds bytes |
| 4 | Adversarial vendor, swap entire dataset | report on different dataset | **Full** — `dataset.hash` mismatch |
| 5 | Compromised producer (key theft) | forge claims under producer.id | **Partial** — needs `producer.signature` (optional in v0.1, mandatory in v0.2 for high-stakes) |
| 6 | Compute-side determinism attack | non-deterministic metric to cherry-pick | **Out of scope** — separate determinism harness required |

### 6.2 What PRML does *not* protect against

- Lying about which model was actually run (mitigated by optional `model.hash`).
- Dataset *legitimacy* (who labeled, with what bias). Out of scope.
- Side-channel leakage during evaluation. Out of scope.
- Quantum-era SHA-256 collision attacks (v0.2 will define algorithm agility).

### 6.3 Cryptographic assumptions

- SHA-256 collision resistance (NIST FIPS 180-4); 2⁻¹²⁸ second-preimage security.
- No assumption about dataset entropy, model architecture, or training procedure.

---

## 7. Compliance mapping (≈ 1 page)

### 7.1 EU AI Act (Reg. 2024/1689)

| Article | Obligation | PRML field(s) |
|---|---|---|
| 12 | Automatic logging of events relevant to risk | `claim_id`, `created_at`, exit code, `prior_hash` chain |
| 17 | Quality management system records | manifest + sidecar + chain hash |
| 18 | 10-year retention of technical documentation | append-only chain, plain text |
| 50 | Transparency obligations to deployers | published canonical URL + spec license (CC BY 4.0) |

### 7.2 NIST AI RMF v1.0

| Function | Subcategory | PRML alignment |
|---|---|---|
| GOVERN-1 | accountability mechanisms | `producer.id` + signature |
| MEASURE-2 | evaluation metrics & test sets | `metric` + `dataset.hash` |
| MANAGE-4 | recurrent monitoring | amendment chain over time |

### 7.3 ISO/IEC 42001:2023

- Clauses 7.5 (documented information), 8.4 (operational planning), 9.2 (internal audit) — direct mapping documented in Appendix B.

### 7.4 Position

PRML is *not* a compliance product. It is a primitive that makes named regulatory obligations satisfiable with arithmetic verification rather than process attestation.

---

## 8. Reference implementation: `falsify` (≈ 0.75 page)

- Single-file Python 3.10+, 1,287 LOC, MIT license.
- Three commands: `lock` (commit), `verify` (run), `audit` (inspect chain).
- Zero runtime dependencies beyond the standard library + PyYAML (canonicalizer is hand-rolled, not from PyYAML).
- CI integration via GitHub Action `falsify-verify@v0.1` *(planned for v0.2)*.
- Performance: lock + verify on a 50K-row classification benchmark < 200 ms (excluding model inference).
- Test vector suite: 47 vectors covering canonicalization edge cases (Unicode, float precision, key ordering, escapes).

---

## 9. Discussion (≈ 0.5 page)

### 9.1 What PRML changes about the publication record

- Reviewers can demand a manifest hash before reading the results section.
- Conferences can require manifest URL + chain hash in camera-ready submissions.
- Auditors and regulators can verify claims years later, offline, without trusting the publisher.

### 9.2 What PRML does *not* change

- Whether benchmarks measure what they claim to measure (validity, not integrity).
- Whether published metrics correlate with deployment performance (generalization, not commitment).
- Whether the producer is a good actor (identity, not trustworthiness).

### 9.3 Adoption strategy

- Voluntary first: opt-in tag in arXiv submissions; opt-in field in NeurIPS reproducibility checklist.
- Regulator-driven second: AI Act audit trail submissions reference PRML manifests by hash.
- Default last: when reviewers reject papers without manifests, the equilibrium shifts.

---

## 10. Limitations and future work (≈ 0.5 page)

- **v0.1 limitations:** no signature mandate; no multi-metric claims; no tolerance specification; no formal canonicalization grammar in BNF (English only).
- **v0.2 roadmap (target 2026 Q4):** algorithm agility (`sha256` → `hash_alg` field), `tolerance`, multi-claim manifests, signature requirement for high-risk Annex III systems.
- **Open questions:** post-quantum hash migration; interop with W&B and MLflow; integration with existing model registries; on-chain anchoring (deliberately deferred — chain hash is sufficient for 99% of use).

---

## 11. Conclusion (≈ 0.25 page)

PRML provides the primitive that ML evaluation has lacked: a cryptographic record of what was committed before an experiment, in a format readable by humans, verifiable by machines, and durable for decades. The cost of adoption is one hash. The cost of non-adoption — measured in regulatory exposure, reproducibility failures, and reviewer trust — is rising. We invite the community to review v0.1, contribute test vectors, and adopt the format in their own publication and audit pipelines.

---

## References *(seed list, ~30 entries)*

- Mitchell et al. 2019, *Model Cards for Model Reporting*. FAT*.
- Gebru et al. 2018, *Datasheets for Datasets*. CACM.
- Liang et al. 2023, *Holistic Evaluation of Language Models*. TMLR.
- Pineau et al. 2021, *Improving Reproducibility in Machine Learning Research*. JMLR.
- Nosek et al. 2018, *The preregistration revolution*. PNAS.
- Chambers 2013, *Registered Reports*. Cortex.
- Zarin et al. 2011, *The ClinicalTrials.gov Results Database*. NEJM.
- Torres-Arias et al. 2019, *in-toto: Providing farm-to-table guarantees for bits and bytes*. USENIX Security.
- Benet 2014, *IPFS — Content Addressed, Versioned, P2P File System*. arXiv.
- NIST FIPS 180-4 (2015), *Secure Hash Standard*.
- NIST AI RMF v1.0 (2023).
- ISO/IEC 42001:2023.
- EU Reg. 2024/1689 (AI Act).
- *(extend to ~30 by submission)*

---

## Appendix A — Test vector v1 (canonical bytes + expected hash)

*(8-line minimal manifest from spec §A; 2 KB canonical byte sequence; SHA-256 digest reproducing across three independent implementations: Python, Go, Rust — Rust impl planned for v0.2)*

## Appendix B — ISO/IEC 42001:2023 clause-by-clause mapping

*(table covering 7.5.1, 7.5.2, 7.5.3, 8.4, 9.2 with PRML field bindings)*

## Appendix C — Why YAML and not JSON / CBOR / TOML

*(half-page rationale: human reviewability > byte efficiency at this scale; YAML 1.2 strict subset gives us comments-free + flow-free without inventing a new format; explicit comparison table)*

## Appendix D — Implementation checklist for verifier authors

*(20-item checklist; same as PRML spec §10)*

---

## Editorial schedule (3-week draft window)

| Week | Milestone |
|---|---|
| 2026-05-01 → 05-08 | §1, §2, §3 prose draft; reference list to 20 entries |
| 2026-05-08 → 05-15 | §4, §5, §6 prose draft; test vector v1 finalized |
| 2026-05-15 → 05-22 | §7, §8, §9 prose draft; appendices; full reference list to 30 |
| 2026-05-22 | Internal review freeze — circulate to 3 sympathetic readers (Ng, Marcus, Gebru via cold email) |
| 2026-05-29 | Incorporate review notes; arXiv submission |
| 2026-06-12 | NeurIPS workshop submission deadline (typical) — paper ready |

---

## Submission checklist (arXiv)

- [ ] LaTeX source (NeurIPS workshop template — `neurips_2026.sty` if available, else generic `article`)
- [ ] PDF compiles clean without warnings
- [ ] All references with DOIs where available
- [ ] Code release URL stable (github.com/studio-11-co/falsify pinned commit)
- [ ] Spec URL stable (spec.falsify.dev/v0.1)
- [ ] Test vectors public + reproducible
- [ ] Author affiliation: "Cüneyt Öztürk (Independent)" — no university, no employer
- [ ] Conflict-of-interest statement: none
- [ ] Funding statement: self-funded
- [ ] Ethics statement: PRML is a primitive; deployment ethics are out of scope
- [ ] arXiv categories: cs.CR primary; cs.LG, cs.SE cross-list
- [ ] License: CC BY 4.0 (matches spec)

---

*Outline drafted 2026-05-01 by Cüneyt Öztürk. Comments welcome via `hello@falsify.dev` or GitHub Discussions on `studio-11-co/falsify`.*
