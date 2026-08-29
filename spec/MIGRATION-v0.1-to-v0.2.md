# Migration guide — PRML v0.1 to v0.2

**Status:** Stable. v0.2 freezes 2026-05-22 23:59 UTC.
**License:** Community Specification License 1.0 (changed from CC BY 4.0 on 2026-08-29)
**Editor:** Cüneyt Öztürk

---

## TL;DR

**Breaking changes: none.**

Every v0.1 manifest remains a valid v0.2 manifest. The SHA-256 hash of a v0.1-shaped manifest computed under v0.2 canonicalisation rules MUST equal the hash computed under v0.1 rules. This is a hard non-negotiable constraint.

If you only consume manifests, no action is required.
If you produce manifests, you may opt into v0.2 optional fields when they add value.

---

## What changed

### Conceptual additions (no field changes required)

1. **§2.3.4 timestamp anchor distinction.** The v0.1 spec received an editorial clarification: the `created_at` field is producer-declared and is included in the hash but is not externally verifiable on its own. Audit-strength timestamps come from anchor mechanisms outside the manifest (git commit time, registry receipt, RFC 3161, Sigstore Rekor, arXiv submission, DOI registration, CI run logs). v0.2 makes this distinction normative: a v0.2-conforming producer SHOULD anchor every published manifest in at least one such mechanism.

2. **Producer identity guidance.** The `producer` field stays a plain string (or v0.1 mapping). v0.2 adds a non-normative recommendation to anchor identity to one or more external artefacts. Identity levels 0–4 are documented in the cookbook (`IDENTITY-LEVELS.md`). The structured `producer: {id, key_id, signature?, sigstore_bundle?}` upgrade is deferred to v0.3.

3. **Selective non-publication remains out of scope.** v0.1 §8.1 stated this; v0.2 restates it as a freeze-day editorial decision. Publication completeness is a registry-policy, journal-policy, or signed-execution-pipeline concern that sits on top of PRML.

4. **Multi-metric claims = multiple manifests.** Until the v0.3 claim-tree design lands, an evaluation suite reporting N metrics is N v0.1/v0.2 manifests with a shared `claim_group` identifier.

### Optional fields (RFC P-01 through P-05)

These are opt-in. Manifests that omit them are valid v0.2.

| Field | Purpose | Default | Conformance |
|---|---|---|---|
| `prml_mode: static \| streaming` | Streaming/continuous-eval support (Chatbot Arena, live drift monitors) | `static` (v0.1 behaviour) | TV-014 |
| `pre_registered_from`, `pre_registered_to` | RFC 3339 window for streaming mode | absent in static | TV-014 |
| `value_method` | Aggregation rule identifier for streaming mode (e.g. `"mean_over_window"`, `"elo_rating"`) | absent in static | TV-014 |
| `runner_attestation` | URI or content-addressed pointer to an external execution attestation (e.g. Sigstore Rekor entry, ValiChord HarmonyRecord) | absent | TV-015 |
| `attestation_uri` | URI to a companion attestation system distinguishing *execution attestation* (Pattern 11) from *independence attestation* (Pattern 13) | absent | TV-015 |
| `revoked_at`, `revocation_reason` | Producer-side revocation marker | absent | TV-016 |
| `seed` constraint relaxed for streaming | Streaming aggregates may use sample-window seeds | unchanged for static | TV-014 |

### Conformance vector additions

Eight new vectors TV-013 through TV-020 at `spec/test-vectors/v0.2/test-vectors.json`. TV-013 demonstrates v0.1 hash-equivalence under v0.2 rules. The full 21-vector suite (13 v0.1 + 8 v0.2) passes byte-equivalent across all four reference implementations as of 2026-05-15.

### Canonicalisation rules

Unchanged. Streaming mode and other v0.2 additions reuse the existing canonicalisation defined in §3 of v0.1. No new escaping, no new normalisation passes, no new key ordering.

---

## Migration paths

### Path A — no action

You publish PRML v0.1 manifests today, your toolchain is fine. v0.2 readers parse your manifests unchanged. Recommended for the 80% case.

### Path B — adopt anchor timestamps

You publish manifests but want stronger audit defense against back-dating.

1. Continue producing v0.1-shaped manifests.
2. Add one or more anchor mechanisms outside the manifest:
   - Commit `.prml.yaml` to a public git repo (git commit timestamp = anchor)
   - POST to `registry.falsify.dev` after lock (registry receipt = anchor)
   - Sign via `cosign sign-blob` (Sigstore Rekor entry = anchor)
3. Optionally embed the anchor URI in `runner_attestation` or `attestation_uri`.

No spec-level changes required.

### Path C — adopt v0.2 optional fields

You produce manifests for use cases v0.1 didn't cover cleanly (streaming evaluation, execution attestation, scheduled revocation).

1. Add `prml_mode: streaming` and the streaming window fields for live leaderboards.
2. Add `runner_attestation` or `attestation_uri` for execution/independence attestation.
3. Add `revoked_at` + `revocation_reason` when retiring a manifest after publication.

Existing v0.1 readers ignore unknown fields per the v0.1 lenient parsing rule. v0.2-aware readers act on them.

### Path D — pair with Sigstore (cookbook Pattern 11)

See `falsify-cookbook/patterns/11-sigstore-execution.md`. Closes execution-integrity gap from §8.1.

### Path E — pair with ValiChord commit-reveal (cookbook Pattern 13)

See `falsify-cookbook/patterns/13-commit-reveal-validation.md`. Closes the independence-attestation gap from §8.1.

---

## Identity levels reference

Identity levels 0–4 describe the binding strength between the `producer` field and the real-world authoring entity. Non-normative in v0.2; normative reference in v0.3.

See `falsify-cookbook/IDENTITY-LEVELS.md`. Brief:

- **Level 0** — unsigned local manifest
- **Level 1** — public git commit or registry timestamp
- **Level 2** — signed commit or detached PGP/minisign signature
- **Level 3** — Sigstore + Rekor transparency log
- **Level 4** — institutional / regulated identity

---

## Deferred to v0.3

The following are tracked in `spec/v0.3-backlog/`:

- **Claim tree / suite manifests** — multi-metric eval batteries (HELM, Big-Bench, LMSYS Arena, LiveCodeBench)
- **Producer cryptographic binding** — structured `producer: {id, key_id, signature?, sigstore_bundle?}`
- **Tolerance / epsilon** — GPU floating-point non-determinism handling

Each has a tracking issue with label `rfc-v0.3` opening when v0.3 RFC starts.

---

## Versioning

PRML follows the canonical version scheme:

- v0.1 — initial public draft (2026-05-01), stable
- v0.2 — first additive release (2026-05-22), stable, this document covers migration
- v0.3 — open, comment window not yet scheduled (target Q4 2026)

---

## Compatibility statement

> A conforming v0.2 implementation MUST verify any v0.1 manifest as if it were a v0.2 manifest with all v0.2 optional fields absent. The hash of a v0.1 manifest, computed with v0.2 canonicalisation rules, MUST equal the hash computed with v0.1 rules.

This is non-negotiable. If any future v0.x change breaks v0.1 hash-equivalence for v0.1-shaped manifests, that change is rejected before consideration.

---

*Editor's note: v0.2 is intentionally a small additive release. Nothing here invalidates a v0.1 reader or producer. The new fields are doors, not walls.*
