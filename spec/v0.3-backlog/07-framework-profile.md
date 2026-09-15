# v0.3 RFC issue: an optional `framework_profile` block

**Status:** backlog, opened 2026-09-15. **Source: outside.** Raised by a third party on
`aiverify-foundation/moonshot#489`, in a comment nobody asked for, by someone with no prior
contact with this project. Inputs welcome.

## Problem

A PRML manifest fixes a measurement contract: metric, comparator, threshold, dataset identity,
seed. That is deliberately narrow, and the narrowness is the point — the bytes that get hashed
are the bar, and nothing else.

But the same measurement is reused under different governance obligations. The commenter put it
plainly: the design should let *"a bank, publisher, or lab rerun the same recipe while attaching
different governance obligations without changing the measurement path."*

Today PRML cannot express that at all. The schema has fourteen properties, none of them about a
framework or a control, and `additionalProperties: false`. A host that wants to record *which*
obligation a run was operationalising has three bad options: put it in `notes` as prose, keep it
in a side file with no binding to the hash, or fork the schema.

## What was proposed

An optional block alongside the measurement fields:

- `framework` / `version` — NIST AI RMF 1.0, ISO/IEC 42001:2023, an EU AI Act obligation set, an
  industry profile
- the control or requirement id being operationalised
- evidence access assumed: public dataset, licensed internal dataset, confidential red-team set
- what the run can decide, e.g. *threshold met for this recipe*
- `does_not_prove`: compliance, model safety, suitability outside this dataset

## Why this is worth taking seriously

**It attacks the objection we actually measure.** Across 32 contacts in the 2026-08/09 sprint the
two substantive rejections were both *ExistProc + NoUrg*: the existing process is felt to cover
it. A block that says "keep your measurement path, the crosswalk is optional metadata" is a
smaller ask than "adopt a record format".

**It matches the one real external integration.** ValiChord did not adopt the format; they kept
their own attestation bundle and added a single `prml_lock_hash` field. Two independent parties
have now converged on the same shape: the discipline plus one binding field travels, the format
does not.

**`does_not_prove` already exists in our writing but not in our bytes.** Every public page carries
a "what this does not prove" section. The manifest itself carries none of it. Putting it in the
record — optional, producer-declared — makes the limit travel with the claim instead of living
only on our website.

## Open questions

- **Inside or outside the hash?** If the block is inside the canonical bytes, changing a crosswalk
  changes the digest, which is wrong: the measurement contract did not change. If it is outside,
  it is unbound metadata and a producer can swap it freely. A sidecar with its own digest,
  referenced from the manifest, is a third option and mirrors `06-signature-sidecar.md`.
- **`additionalProperties: false` is load-bearing.** It is why unknown fields cannot silently
  change canonical bytes across implementations. Any profile block has to be added explicitly to
  the schema, not allowed in by relaxing that.
- **Vocabulary drift.** Framework names and control ids change (see Regulation (EU) 2026/1744
  renumbering work, 2026-09-14). A free-text `control_id` will rot. An enum will be wrong within a
  year. Undecided.
- **Scope creep risk.** PRML's value is that it refuses to be a compliance artifact. A profile
  block is one step toward looking like one. The `does_not_prove` field is a partial guard, but
  the failure mode — a reader treating a PRML receipt as evidence of compliance — gets easier, not
  harder, with this block present.

## Related

- `05-sealed-disclosure.md` (what stays private), `06-signature-sidecar.md` (the sidecar pattern)
- ValiChord `valichord_attestation/bundle.py`, field `prml_lock_hash`
- Source comment: `aiverify-foundation/moonshot#489`, 2026-09-15
