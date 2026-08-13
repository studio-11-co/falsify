# PRML v0.2 RFC — comments received and their disposition

**Status:** published 2026-08-13, fulfilling the freeze-record commitment ("a
list of comments received and their disposition will be published as
`spec.falsify.dev/v0.2-comments` after the freeze").
**Comment window:** 2026-05-08 → 2026-05-22 23:59 UTC (14 days)
**Channels:** GitHub Discussion #11 · issues with label `rfc-v0.2` · email `[v0.2 RFC]`
**Editor:** Cüneyt Öztürk · hello@falsify.dev · Falsify OÜ (reg. 17574308, Estonia)

---

## Honest tally

One external commenter participated in the window: **Ceri John (Topeuph AI /
ValiChord)**, via [Discussion #11](https://github.com/studio-11-co/falsify/discussions/11).
No comments arrived via labelled issues or email. No institutional comments
(JTC 21, AISI, audit firms) were received. This page does not pretend
otherwise — the disposition record below is short because the input was.

## Comments and dispositions

### C-1 — P-02: execution vs independence attestation (Ceri John, 2026-05-20)

**Position:** support, with a distinction.
**Substance:** P-02's `runner_attestation` conflated two different things:
*execution attestation* (who ran the eval and when — Sigstore territory,
Cookbook Pattern 11) and *independence attestation* (verdicts produced by
parties that could not coordinate outcomes — commit-reveal territory).
These address different parts of the §8.1 gap and are complementary.
**Disposition: ACCEPTED.** Landed verbatim, with attribution, as freeze-day
decision 5 in the frozen RFC. Follow-on: Pattern 13 (blind commit-reveal
validation) shipped in the cookbook as a co-authored entry (Öztürk & John,
CC0-1.0), and Pattern 11 gained the same attribution metadata block.

### C-2 — v0.3 claim-tree: `samples_total` analog (Ceri John, 2026-05-22)

**Position:** cross-pollination for the deferred claim-tree proposal.
**Substance:** ValiChord's `valichord_attestation` Merkle bundles commit a
`samples_total` count upfront, before any leaf is revealed — the same move
answers the claim-tree open question on partial-publication detection
(`leaves_total` committed before leaves).
**Disposition: ACCEPTED into the v0.3 backlog** (not v0.2 — arrived on
freeze day against a deferred proposal). Recorded in
`spec/v0.3-backlog/01-claim-tree.md` (commit `efcf86f`) with attribution,
citing ValiChord v0.5.3 / `valichord_attestation` 1.2.0.

## Proposal-by-proposal state after the freeze

| Proposal | State | Notes |
|---|---|---|
| P-01 streaming variant | **OPEN** | The `value_method` vocabulary question received no comments. Not resolved unilaterally; carried to promotion review. |
| P-02 runner attestation | **OPEN**, sharpened | Single-vs-list question received no comments. The execution/independence distinction (C-1) is in the freeze record. `prml-linkage/0` (draft, 2026-08-13) is a concrete candidate for what an execution-side URI points to — see below. |
| P-03 revocation | **OPEN** | The revocation-signature question received no comments. Carried. |
| P-04 conformance vector format | **IMPLEMENTED** (2026-08-13) | The vector directory format now exists at `spec/test-vectors/v0.1/vectors/` (13 vectors as `<id>/manifest.yaml` + `<id>/expected_hash.txt`), and the CLI grew the proposed command: `falsify conform "<target>"` runs every vector through a target implementation and reports byte/hash equivalence. Informative, as proposed. |
| P-05 patent grant placement | **ACCEPTED, pending promotion** | Uncontroversial editorial move (Appendix C → §1.5 preamble). It applies to the v0.2 *final* text, which does not exist yet; it will be executed at promotion, not patched into the frozen RFC. |

## What promotion still requires

The frozen RFC's own rule stands: P-01, P-02, P-03 are not resolved
unilaterally. Promotion to v0.2-final waits for external reviewers with
implementation stakes — eval-framework maintainers, auditors, or standards
bodies. Until then v0.1 remains the stable spec, and v0.2 remains a frozen
RFC whose backwards-compatibility guarantee (v0.1 hash-equivalence) is
already exercised by the conformance suite.

## Related work since the freeze (context, not comments)

- **`prml-linkage/0` draft** (2026-08-13): adapter-independent execution
  linkage — start/final record chaining with strength tiers L1–L3.
  Addresses the "already ran" gap named in P-02 review and by the Andes
  interoperability assessment. `spec/linkage/prml-linkage-0.md`.
- **v0.3.x integrity releases** (July 2026): YAML parse parity across
  implementations, RFC 3161 + Rekor anchoring on the registry — these
  strengthen the anchor-timestamp semantics that freeze decision 3 leans on.
