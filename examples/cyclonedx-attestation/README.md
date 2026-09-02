# cyclonedx-attestation — a PRML receipt as CycloneDX attestation evidence

For teams whose assurance workflow already speaks CycloneDX: this is a
CycloneDX 1.6 BOM whose `declarations` block attests one thing about one
component, with the evidence for it carried as PRML artefacts.

- `bom.cdx.json` — the attestation BOM (schema-valid CycloneDX 1.6)
- `manifest.prml.yaml` — the pre-registered manifest the evidence refers to
- `validate.py` — validates the BOM against the 1.6 schema, then re-derives
  the PRML evidence offline (hash of the manifest, verdict for the observed
  value)

## What is being attested

Component: `falsify` 0.3.14 (the PRML reference implementation).
Evaluation: its own conformance run against the PRML v0.1 test vectors.

Two requirements, defined inside the BOM (`definitions.standards`):

| Requirement | Claim | Evidence |
|---|---|---|
| REQ-1 The acceptance criterion was fixed before the run | bar `conformance_vectors_passing >= 21.0` committed to SHA-256 `390e78d9…5590c`, timestamped 2026-07-30T12:18:14Z | manifest, RFC 3161 token, Rekor entry (log index 45932166) |
| REQ-2 The observed result meets that criterion | observed 21 → PASS | verifier output |

The `prml:*` values sit on the component as properties, using the
[`prml` namespace registered in the CycloneDX property taxonomy](../../spec/compliance/cyclonedx-property-taxonomy.md).
The `evidence` entries point at the artefacts by URL, so the BOM stays small and
the artefacts stay where anyone can fetch them without an account.

## Why this exists

A CycloneDX ML-BOM records what was measured (`modelCard.quantitativeAnalysis`).
It has no slot for *when the pass bar was fixed*. Attestations (CDXA) add
claims, evidence and an assessor; what they still need is evidence a consumer
can check without trusting the assessor. A PRML receipt is that: a hash of the
criteria, a third-party time on the hash, and a verifier anyone can run.

## What it does not prove

Stated inside the BOM, in each claim's `reasoning`, so it travels with the file:
the receipt proves the bar existed no later than the timestamp. It does not by
itself prove the evaluation ran after that moment, and it says nothing about
whether the result is correct. This example is a self-attestation
(`thirdParty: false`); the confidence scores say so.

## Run it

```
pip install jsonschema pyyaml
python3 validate.py
```

Expected: `schema: OK | prml: OK`. The schema check needs network once (it
caches the three CycloneDX schema files); the PRML check is fully offline.

The record used here is the registry's own, chosen because it is real and
anchored (Sigstore TSA + Rekor) rather than synthetic. Replace the manifest, the
hash and the URLs with your own record; nothing else in the BOM depends on the
values.
