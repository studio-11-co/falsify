# PRML v0.2 paper — outline

**Status:** Outline. To be drafted post-RFC freeze (2026-05-22) and revised through 2026-Q3.
**Target venue (primary):** arXiv cs.SE (replacement of v0.1 preprint)
**Target venue (secondary):** REFORMS-style workshop at NeurIPS 2026 / ICML 2027 — community feedback, not formal review
**Length target:** 16–18 pages (v0.1 was 14 pages; v0.2 adds 4 sections + appendix)
**Co-authors:** Cüneyt Öztürk (lead). Open seat for one community co-author who reviewed v0.2 RFC substantively.

---

## Working title options

1. **"PRML v0.2: Streaming, Revocation, and the Boundaries of a Pre-Registration Primitive for Machine Learning Evaluation"**
2. "Closing Three Gaps in PRML v0.1: Streaming Evaluations, Revocation Semantics, and Runner Attestation"
3. "Pre-Registered ML Manifests, Revisited: What 14 Days of Public Comment Taught Us"

Default: option 1. Picks up from the v0.1 paper's title pattern; signals what's new without being defensive.

---

## Abstract (target ≤ 200 words)

> PRML v0.1 (Öztürk, 2026) introduced a content-addressed YAML serialisation that binds a pre-registered ML evaluation claim to a SHA-256 hash. The format covered the canonical case — a single batch evaluation against a fixed threshold — and deliberately deferred three classes of claim: live streaming evaluations, post-publication retractions, and runtime execution attestation. v0.2, frozen on 2026-05-22 after a 14-day public comment window, addresses these gaps additively. We introduce four optional fields (`prml_mode`, `value_method`, `runner_attestation`, `revoked_at` / `revocation_reason`) and one structural change (the patent non-assertion grant moves from the appendix into the preamble). Every v0.1 manifest remains a valid v0.2 manifest, and the canonicalisation rules preserve hash-equivalence for v0.1-shaped inputs across the four reference implementations. We report the 27 substantive comments received during the RFC window, the 11 changes incorporated and 16 deferred, and a calibration study against the 13 v0.1 conformance vectors plus 8 new v0.2 vectors. The spec is licensed under the Community Specification License 1.0 (v0.1 copies distributed before 29 August 2026 remain under CC BY 4.0); the reference implementations are MIT; the patent non-assertion grant is reproduced verbatim in §1.5.

---

## Section structure

### §1 Introduction (≈2 pages)

- §1.1 What v0.1 closed and what it left open (3 paragraphs)
- §1.2 Three motivating cases that arose during the v0.1 launch
  - A live Elo-style evaluation that did not fit `prml_mode: static`
  - A post-publication dataset contamination event with no in-spec retraction path
  - A federally-funded audit that asked "what was actually run?" rather than "what was committed?"
- §1.3 Contributions
- §1.4 Non-goals — explicitly preserved from v0.1
- §1.5 Patent non-assertion grant (moved here per CEN-CENELEC P-05; full text)

### §2 Background and related work — minimal updates from v0.1 (≈1.5 pages)

- §2.1 Updates to "Pre-registration in adjacent fields" — referencing the JTC 21 / EU AI Act Article 12 mapping work that landed during the v0.1 cycle
- §2.2 New: "Streaming evaluation primitives" — survey of how Chatbot Arena, AlpacaEval live, and production A/B systems handle the threshold-commitment question (or fail to)
- §2.3 New: "Retraction in cryptographic commitment systems" — brief: how transparency logs (Sigstore/Rekor), Certificate Transparency, and software supply-chain (in-toto) handle revocation; what PRML's narrower scope adopts and what it doesn't
- §2.4 Cross-reference to v0.1 paper for unchanged background (compute, content-addressed systems)

### §3 The four v0.2 additions (≈4 pages — the meat)

For each addition: motivation paragraph → schema diff → byte-level canonicalisation rule → worked example → known limit.

- §3.1 P-01: Streaming variant (`prml_mode`, `value_method`, `pre_registered_from/to`, `sample_size` as minimum)
  - Worked example: 30-day Chatbot Arena window, Elo aggregation rule
  - Limit: streaming hash commits the *protocol*, not the *answer*; consequence for verification
- §3.2 P-02: Runner attestation (`runner_attestation` URI)
  - Worked example: Sigstore-attested runner emitting a Rekor log entry
  - Limit: PRML records that an attestation was emitted, not what it contains
- §3.3 P-03: Revocation primitive (`revoked_at`, `revocation_reason` controlled vocab)
  - Worked example: dataset_compromised retraction on a published manifest
  - Limit: revocation is signal, not authority — the original hash continues to verify
- §3.4 P-04: Conformance vector format
  - The directory layout, the runner protocol (stdin JSON → stdout JSON)
  - 8 new v0.2 vectors named and cited from `spec/test-vectors/v0.2/`
  - Coverage analysis: which v0.2 features each vector exercises

### §4 Backwards compatibility (≈1 page)

- §4.1 The non-negotiable property: any v0.1 manifest produces the same hash under v0.2 canonicalisation rules
- §4.2 Empirical check: all 13 v0.1 vectors run against the patched v0.2 reference implementations; results table
- §4.3 What this rules out: any v0.2 change that requires re-canonicalising v0.1 inputs is rejected at design time

### §5 The RFC process itself (≈2 pages — methodological)

- §5.1 Process: 14-day public comment window, GitHub issues + email, daylight rule (no off-record discussion changes the spec)
- §5.2 Comment volume and disposition
  - Total comments received
  - Per-proposal breakdown (P-01 through P-05)
  - Adopted: N. Modified: M. Deferred to v0.3+: K. Rejected as out-of-scope: J.
- §5.3 What changed between RFC and final v0.2 — annotated diff
- §5.4 Open question: was the 14-day window long enough? Empirical reading of comment-arrival distribution.

### §6 Implementation report (≈1.5 pages)

- §6.1 Patches to falsify (Python), prml-js (Node), prml-go, prml-rust
- §6.2 Lines of diff per implementation
- §6.3 Conformance test results: 13 v0.1 vectors + 8 v0.2 vectors against each impl
- §6.4 Inspect AI upstream RFC status
- §6.5 falsify-inspect adapter — operating below the upstream change in case it doesn't land

### §7 Threat model — updates only (≈1 page)

- §7.1 New attack surfaces introduced by streaming mode (window-rolling, eval timing manipulation)
- §7.2 New attack surfaces introduced by revocation (selective revocation as quiet retraction)
- §7.3 What PRML still doesn't defend against — selective publication still stands as the §8.1 limit, now §9.1

### §8 Compliance mapping — updates (≈1 page)

- §8.1 EU AI Act Article 12 mapping: how runner_attestation field interacts with 12(2)(b) traceability
- §8.2 ISO/IEC 42001:2023 — updated clause references
- §8.3 NIST AI RMF — Govern.5.2 updates per v0.2 revocation primitive
- §8.4 JTC 21 input — status of the comment paper submitted 2026-05-15

### §9 Limitations (preserved from v0.1, expanded) (≈1 page)

- §9.1 Selective publication (preserved verbatim from v0.1 §8.1)
- §9.2 Bit-level float determinism (deferred to v0.3 with tolerance field)
- §9.3 Multi-claim manifests (still single-claim per manifest; composition is a registry concern)
- §9.4 Algorithm agility (sha256 only in v0.2; post-quantum migration is v0.3+)
- §9.5 Runner attestation does not specify what makes an attestation valid

### §10 Discussion (≈1 page)

- §10.1 What we learned from the v0.1 launch about distribution
- §10.2 Why "additive only" mattered — and what it cost (rejected ideas summary)
- §10.3 The integrity index pattern — what surfacing format-hygiene scores publicly did
- §10.4 RFC-process implications for future ML standards

### §11 Conclusion (≈0.5 pages)

Same shape as v0.1 conclusion: the cost of adoption is one hash function call; the cost of non-adoption is the gap that v0.1 named and v0.2 closes by addition. v0.2 preserves v0.1 canonicalization and hashes for valid v0.1 manifests. We invite the community to adopt the format in publication and audit pipelines. v0.3 freeze is targeted for early 2027.

### Appendices

- A. Updated canonical-bytes ABNF grammar (v0.2 fields)
- B. Updated ISO/IEC 42001:2023 clause-by-clause mapping
- C. The 8 new v0.2 conformance vectors (verbatim with hashes)
- D. The full RFC comment archive (from `spec.falsify.dev/v0.2-comments`)
- E. Patent non-assertion grant (full text — moved from §1.5 reference)

---

## Figure / table inventory

- Fig 1 — schema diff between v0.1 and v0.2 (visual; used in §3 intro)
- Fig 2 — streaming-mode timeline showing `pre_registered_from/to` window vs batch `pre_registered` (§3.1)
- Fig 3 — revocation status overlay on a registry page (§3.3)
- Tab 1 — full canonicalisation rule list for v0.2 (§3 intro)
- Tab 2 — backwards-compatibility check: 13 v0.1 vectors × 4 implementations × 2 spec versions (§4.2)
- Tab 3 — RFC comment disposition by proposal (§5.2)
- Tab 4 — implementation diff summary (§6.2)

---

## Drafting timeline

| Window | Step |
|---|---|
| 2026-05-23 → 2026-05-29 | RFC freeze; final draft of v0.2 spec; conformance vectors locked |
| 2026-05-30 → 2026-06-13 | First-pass paper draft (Cüneyt) |
| 2026-06-14 → 2026-06-20 | Internal review (author + 1–2 trusted external reviewers) |
| 2026-06-21 → 2026-06-30 | Revision; arXiv replacement upload |
| 2026-Q3 | REFORMS-style workshop submission window |

---

## Constraints

- **Voice rule (preserved from v0.1):** straightforward, no marketing register. The paper documents a primitive; it does not advocate for adoption beyond what the math supports.
- **Citation rule:** every claim about external systems (Inspect, HELM, JTC 21) must cite a public artefact, not informal communication.
- **Honesty rule:** the RFC comment volume is what it is. If only 5 substantive comments arrived, report 5. Do not pad with our own questions.
- **Scope rule:** if a topic exceeds the page budget, defer to a follow-up paper rather than truncate.

---

## Open authorship questions

1. Should the integrity-index methodology paper be a separate venue submission or an appendix here? Default: separate (different audience).
2. Should the JTC 21 comment paper be referenced inline or attached as supplementary? Default: referenced inline; supplementary materials grow out of hand fast.
3. Should `falsify-inspect` get its own paper at a tools track? Plausible but low priority; mention in §6.4 and revisit only if Inspect upstream lands.

---

*Outline CC0; reuse, fork, edit. Drafting begins after 2026-05-22 freeze.*
