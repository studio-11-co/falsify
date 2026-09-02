# `prml` — CycloneDX Property Taxonomy

This document defines the official `prml` property namespace for
[CycloneDX](https://cyclonedx.org/) BOMs, administered by the maintainers of the
[PRML specification](https://spec.falsify.dev/v0.1) (Pre-Registered ML Manifest —
an open format, published under the Community Specification License 1.0 with
MIT-licensed reference implementations, that commits an ML evaluation's success
criteria to a SHA-256 hash before the run).

Purpose: a CycloneDX `modelCard.quantitativeAnalysis.performanceMetrics` entry
records what was measured. The `prml` properties let the same BOM carry the
evidence that the pass bar for that measurement was fixed **before** the run,
verifiable offline by any consumer of the BOM.

| Property | Description |
|----------|-------------|
| `prml:manifest:canonical-sha256` | SHA-256 over the PRML canonical bytes of the manifest that pre-registered this evaluation (64 lowercase hex). |
| `prml:manifest:claim-id` | The manifest's `claim_id` (UUIDv7), for cross-referencing the published manifest. |
| `prml:manifest:url` | URL where the manifest text (or its sealed commitment) is published. |
| `prml:receipt:rfc3161-tst` | Base64 RFC 3161 timestamp token over the canonical hash, or a URL to the `.tsr`. |
| `prml:receipt:transparency-log` | Reference to an append-only transparency-log entry for the commitment (e.g. a Rekor log index). |
| `prml:verify:observed` | The observed value later checked against the pre-registered comparator/threshold. |
| `prml:verify:verdict` | `PASS` or `FAIL` as returned by a conforming PRML verifier for the observed value. |

## Placement

Put the `prml:*` properties on the component whose evaluation they describe (the
same place a `modelCard` sits). CycloneDX `declarations.evidence` entries carry no
free-form properties; when the BOM also carries attestations, each evidence entry
points at the artefact by URL and names the taxonomy key it substantiates in
`propertyName`. A complete, schema-valid 1.6 attestation built this way, with a
validator that re-derives the hash and the verdict offline, is in
[`examples/cyclonedx-attestation`](../../examples/cyclonedx-attestation/).

Verification is offline: a consumer recomputes the canonical hash from the
manifest text and compares comparator/threshold to the observed value.
Reference implementations (Python, JavaScript, Go, Rust), 21 positive and 20
negative conformance vectors: <https://github.com/studio-11-co/falsify>.

Contact: `hello@falsify.dev`.
