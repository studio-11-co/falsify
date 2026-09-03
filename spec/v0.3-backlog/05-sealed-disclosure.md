# v0.3 RFC issue: sealed commitments and selective disclosure

**Status:** backlog, opened 2026-09-03. Inputs welcome.

## Problem

A PRML manifest commits nine fields to one canonical byte sequence and one
SHA-256. Publication is therefore all-or-nothing: either the whole manifest
is public, or a verifier sees only a hash and learns nothing about which
criteria it binds.

Three classes of evaluation cannot publish their criteria and still need a
checkable "the bar existed before the result":

- dangerous-capability evaluations whose thresholds and test contents are
  withheld for infohazard reasons (a 2026 SAIF report notes that this opacity
  "makes it difficult to independently assess the quality of the evaluations
  and verify claims about model safety");
- audits in which the criteria come from the audited party and are
  commercially confidential (for example DSA Article 37 audits, where the
  provider supplies the benchmarks the auditor's criteria are built from);
- disclosure regimes that publish figures only as bands or tiers.

## What exists today (registry-level, v0.1 unchanged)

`registry.falsify.dev` accepts **sealed commits** (2026-09-03): the manifest
is validated, canonicalized, hashed, signed and anchored, the text is
withheld, and `POST /<hash>/reveal` publishes it only if the supplied bytes
re-derive the hash. This is a registry service, not a spec change: a sealed
manifest is an ordinary v0.1 manifest whose bytes the producer keeps private.

## Proposed v0.3 direction: field-level commitments

Reuse the leaf/`suite_hash` machinery of issue 01 (claim tree) at the field
level: each of the nine fields becomes a leaf `H(field_name || canonical
value || per-field salt)`, the manifest hash becomes the root over the sorted
leaves, and a producer can reveal any subset of fields with their salts and
Merkle paths. A verifier can then check, for example, that the threshold was
committed before the run while the dataset identity stays private, or the
reverse.

Properties to preserve: byte-equivalence across the four implementations;
deterministic canonical form; `TAMPERED` semantics for any leaf whose
revealed value does not match its commitment.

## Open questions

1. Salt derivation: random per field (stored by the producer) versus derived
   from a single manifest secret (one value to keep). Loss of the secret
   makes the sealed fields permanently unverifiable; is that acceptable?
2. Should the plain v0.1 hash remain the canonical identifier, with the
   field-level root carried as an optional second commitment, so that a
   sealed manifest still has exactly one `claim_id`/hash pair?
3. Registry interaction: does a field-level reveal go through
   `/<hash>/reveal` (partial body) or a new route?
4. Interaction with issue 03 (tolerance): a revealed threshold with a
   pre-committed reading rule for near-threshold results.

## Not in scope

Proving that the evaluation ran after the commitment (execution linkage,
`prml-linkage/0`); confidentiality of the *result* (PRML commits criteria,
not outcomes).
