# v0.3 RFC issue: the governance profile — `prml-profile/0`

**Status:** backlog, opened 2026-09-15, draft format added the same day. **Source: outside.**
Raised by a third party on `aiverify-foundation/moonshot#489`, unprompted, by someone with no
prior contact with this project. Inputs welcome.

## Problem

A PRML manifest fixes a measurement contract: metric, comparator, threshold, dataset identity,
seed. That narrowness is the point — the bytes that get hashed are the bar and nothing else.

But one measurement gets reused under different governance obligations. The commenter put it
plainly: the design should let *"a bank, publisher, or lab rerun the same recipe while attaching
different governance obligations without changing the measurement path."*

Today PRML cannot express that at all. The v0.1 schema has fourteen properties, none about a
framework or a control, and `additionalProperties: false`. A host that wants to record *which*
obligation a run operationalised has three bad options: prose in `notes`, a side file with no
binding to the hash, or a schema fork.

## The design decision that drives everything

**The profile must not live inside the manifest.** If it did, a bank and a publisher attaching
different obligations to the same measurement would produce different canonical bytes and
different digests — and the claim "this is the same bar" would stop being provable across
contexts. That is precisely the property the proposal exists to preserve.

So the relation is inverted: **the profile is its own record and it names the manifest.**
One manifest, zero or many profiles. The manifest never mentions them and its digest never moves.

This mirrors `06-signature-sidecar.md`: the thing that would disturb the bytes lives outside them
and points inward.

## Proposed format — `prml-profile/0`

A PRML-family YAML document, canonicalised by **§3** (same rules, same grammar §3.6) so it can be
hashed and anchored exactly like a manifest.

```yaml
version: prml-profile/0
subject: 1a3466cc08ee7fb60a726ea1c4db6ecf48a9f847b9b7523bfb54b2ffaefee546
framework:
  id: NIST AI RMF 1.0
  uri: https://doi.org/10.6028/NIST.AI.100-1
  retrieved: '2026-09-15'
control: MEASURE 2.3
evidence_access: public-dataset
decides: the accuracy threshold recorded in the subject manifest was met for this dataset
does_not_prove:
  - compliance with the named framework
  - model safety
  - suitability outside this dataset
declared_by:
  id: example.org
declared_at: '2026-09-15T09:00:00Z'
```

| Field | Rule |
|---|---|
| `version` | literal `prml-profile/0` |
| `subject` | 64 lowercase hex — the SHA-256 of the manifest's canonical bytes. **Required.** The profile is meaningless without the measurement it annotates. |
| `framework.id` | free text. **No enum**, deliberately: control vocabularies rot. Regulation (EU) 2026/1744 renumbered AI Act articles between our own surfaces being written and 2026-09-14; an enum frozen in a spec would have been wrong within a year. |
| `framework.uri` | the primary source, not a finding aid. A reader must be able to reach the text the `control` refers to. |
| `framework.retrieved` | ISO date. This is what lets a later reader judge whether the citation has rotted, and it is the same discipline the corpus notes use. |
| `control` | the requirement id being operationalised, as the framework spells it. Free text for the same reason. |
| `evidence_access` | one of `public-dataset`, `licensed-internal`, `confidential`. Says what a third party could re-run, not what the result was. Composes with `05-sealed-disclosure.md`. |
| `decides` | one sentence: what this run can settle. Must be scoped to the subject manifest. |
| `does_not_prove` | list, **required, non-empty**. See below. |
| `declared_by` | same shape as `producer` in the manifest. **May differ from the manifest's producer** — the point is that an auditor or deployer can annotate someone else's measurement. |
| `declared_at` | RFC 3339 UTC. |

## `does_not_prove` is required, and that is the whole safety argument

This block is the one part of PRML that makes the record look like a compliance artifact. That is
a real risk and it gets worse, not better, with the block present.

Requiring `does_not_prove` inverts it: **you cannot attach a governance crosswalk without stating,
in the same bytes, what it fails to establish.** Every public page we publish already carries a
"what this does not prove" section; today none of that travels with the claim. Here it does, it is
producer-declared, and it is hashed.

A profile with an empty or missing `does_not_prove` is **invalid**, not merely discouraged.

## Verifier behaviour

- A verifier **MAY** read profiles.
- A verifier **MUST NOT** let a profile change the manifest's hash, the comparator verdict, or any
  exit code. A profile is annotation, never evidence about the measurement.
- A profile whose `subject` does not match the manifest under examination is reported as
  **profile mismatch**, and the manifest verdict is unaffected.
- Multiple profiles for one manifest is normal and is not a conflict, even when they name
  different frameworks or contradict each other on `decides`. Resolving that is the reader's job.
- **No conformance level requires profiles.** Absence is not a defect.

## Compatibility

Nothing here touches canonical bytes, digests or validation of the manifest. `additionalProperties:
false` stays exactly as it is — it is load-bearing, it is why an unknown field cannot silently move
canonical bytes across four implementations, and this proposal does not relax it. A verifier that
ignores profiles is unchanged and stays conformant.

## Open questions

- **Anchoring.** Should a profile get its own RFC 3161 timestamp? Argument for: an auditor's
  crosswalk has its own chronology worth fixing. Argument against: it invites reading the profile
  as time-proven compliance, the exact misreading the block already risks.
- **Revocation.** A framework citation rots or a control is renumbered. Is there a withdrawn
  profile, or does a new profile simply supersede by `declared_at`? `COMPATIBILITY.md` §5 has a
  `withdrawn:` mechanism for vectors that is not implemented anywhere yet.
- **Registry display.** Whether `registry.falsify.dev` accepts profiles, and whether showing a
  framework name next to a receipt does more harm than good, is a registry question, not a
  specification one. Current instinct: do not display framework names on the public board.
- **Does this earn its place?** PRML's value is that it refuses to be a compliance artifact. The
  honest case against this entire issue is that the narrowness is the product, and that a host
  wanting a crosswalk can keep one in its own system with the manifest hash as the join key —
  which is exactly what ValiChord did with `prml_lock_hash`, without needing anything from us.

## Test vectors to write if this advances

| Case | Expectation |
|---|---|
| PV-001 | well-formed profile, `subject` matches → **valid**, manifest verdict unchanged |
| PV-002 | `subject` points at a different manifest → **profile mismatch**, manifest verdict unchanged |
| PV-003 | `does_not_prove` absent or empty → **invalid profile** |
| PV-004 | two profiles, same subject, different frameworks → both **valid**, no conflict raised |
| PV-005 | profile present, threshold in the manifest altered → manifest **hash mismatch** as usual; the profile must not mask it |

## Related

- `05-sealed-disclosure.md` (what stays private) · `06-signature-sidecar.md` (the outside-the-bytes
  pattern this follows)
- ValiChord `valichord_attestation/bundle.py`, field `prml_lock_hash` — the same shape arrived at
  independently, in shipped code
- Source comment: `aiverify-foundation/moonshot#489`, 2026-09-15
