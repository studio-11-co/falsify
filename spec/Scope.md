# Scope

This file has the meaning given to "Scope" in Section 9.13 of the
[Community Specification License 1.0](./LICENSE.md). It bounds the patent
commitments made by Contributors to, and Licensees of, the PRML specification.

Changes to this Scope are not retroactive.

## In scope

The PRML Working Group develops a specification for **recording, before an
evaluation is run, the criteria by which that evaluation will be judged, in a
form a third party can verify afterwards.**

Specifically, the following are within Scope:

1. **The manifest format.** The set of required and optional fields of a PRML
   manifest, their names, types, value domains and semantics — including the
   nine required fields (`version`, `claim_id`, `created_at`, `metric`,
   `comparator`, `threshold`, `dataset`, `seed`, `producer`).

2. **Canonicalisation.** The rules that map a manifest to a single canonical
   byte sequence: character encoding, Unicode normalisation, key ordering,
   number and string forms, line endings, and the treatment of documents that
   cannot be canonicalised.

3. **The commitment.** The derivation of a digest over those canonical bytes,
   and the binding of that digest to an external time assertion (for example an
   RFC 3161 timestamp token or a transparency-log inclusion proof).

4. **Verification semantics.** The verdicts a conforming verifier produces, the
   conditions under which each verdict is produced, and the process exit codes
   that carry them.

5. **The amendment chain.** How a later manifest references an earlier one, and
   what a verifier concludes from such a chain.

6. **Conformance material.** The positive and negative conformance vectors, and
   the rules by which an implementation is judged conforming.

7. **Serialisations and identifiers** of the above, including media type
   registrations and schema documents published by the Working Group.

## Out of scope

The following are explicitly **outside** Scope, and no patent commitment is made
with respect to them under the Community Specification License 1.0:

- The design, training, tuning, serving or internal behaviour of any machine
  learning model or system that is the subject of an evaluation.
- Evaluation methodology as such: the choice of metric, benchmark, dataset,
  statistical procedure or acceptance threshold, and any claim about whether a
  particular metric or threshold is appropriate.
- The construction, curation, licensing or distribution of datasets.
- Cryptographic primitives themselves (hash functions, signature schemes,
  timestamping protocols, transparency logs) and their implementations. PRML
  references such primitives; it does not define them.
- Registry, storage, retention, billing, access-control, notification and
  user-interface systems built around PRML manifests, including any operated by
  Falsify OÜ.
- Any determination of whether an evaluation result is correct. PRML records
  that a bar was fixed and when; it makes no assertion that the observed result
  is true.

## Note on the source code

Source code developed by the Working Group is governed by the licence in the
repository holding that code, per Section 4 of the Community Specification
License 1.0. The `falsify` reference implementations are published under the
MIT License; see the repository root `LICENSE`.
