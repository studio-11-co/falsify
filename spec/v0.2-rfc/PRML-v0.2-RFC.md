# PRML v0.2 — RFC

**Status:** Frozen — v0.2.0 (2026-05-22). The comment window has closed.
**Editor:** Cüneyt Öztürk · hello@falsify.dev
**Comment window:** 2026-05-08 → 2026-05-22 (14 days)
**Freeze date:** 2026-05-22, 23:59 UTC
**Final draft expected:** 2026-05-29
**Spec home:** spec.falsify.dev/v0.2-rfc (this document)
**License:** CC BY 4.0 — same as v0.1

---

## How to comment

1. **GitHub issues** at `github.com/studio-11-co/falsify/issues` with label `rfc-v0.2`. Preferred for normative concerns.
2. **Email** the editor at `hello@falsify.dev` with subject prefix `[v0.2 RFC]`. Preferred for confidential or institutional comments (JTC 21, AISI, audit firms).
3. **Pull request** against this document for prose-level edits.

A comment that lands by **2026-05-22 23:59 UTC** can change the freeze. A comment after that date is logged and rolled into v0.3 unless it identifies a security flaw.

## Goals of v0.2

v0.1 was scoped narrowly: nine fields, one hash, no I/O. v0.2 keeps that core unchanged and adds the smallest possible set of optional extensions to address gaps that surfaced during the v0.1 launch.

**v0.2 explicitly does not aim to:**
- Replace v0.1 — every v0.1 manifest remains a valid v0.2 manifest
- Add fields that mandate runtime infrastructure
- Solve selective publication (still §8.1)
- Solve execution-time attestation (deferred to v0.3)

## Compatibility statement

> A conforming v0.2 implementation MUST verify any v0.1 manifest as if it were a v0.2 manifest with all v0.2 optional fields absent. The hash of a v0.1 manifest, computed with v0.2 canonicalisation rules, MUST equal the hash computed with v0.1 rules. We will publish a conformance vector set that exercises this property.

This is non-negotiable. If any proposed v0.2 change breaks v0.1 hash-equivalence for v0.1-shaped manifests, that proposal is rejected before consideration.

The conformance vector set that exercises this property is shipped at `spec/test-vectors/v0.2/test-vectors.json` (TV-013 through TV-020, eight vectors). TV-013 specifically demonstrates a v0.1-shaped manifest hashing identically under v0.2 rules. All four reference implementations (Python, JS, Go, Rust) pass 21/21 vectors byte-for-byte as of 2026-05-15.

## Proposals open for comment

### P-01 — Streaming / continuous-eval variant

**Problem.** Live systems (Chatbot Arena, A/B-tested production models, drift monitors) cannot pre-register a single threshold because the threshold *is* the live measurement.

**Proposal.** Add an optional `prml_mode` field with values `static` (default, current v0.1 behaviour) or `streaming`. In streaming mode:

- `pre_registered` becomes a window: `pre_registered_from` and `pre_registered_to` (RFC 3339 timestamps)
- `value` is replaced by `value_method` — a string identifier of the aggregation rule (e.g. `"mean_over_window"`, `"trimmed_mean_5pct"`, `"elo_rating"`)
- `sample_size` becomes a minimum, not an exact figure

**Example** (matches conformance vector TV-014 byte-for-byte; this is the canonical shape — `version: prml/0.2`, `comparator` not `threshold_direction`, `dataset` as a mapping, `model.id` not `model_version`):

```yaml
claim_id: 01900000-0000-7000-8000-000000000014
comparator: '>='
dataset:
  hash: n/a-streaming
  id: lmsys-arena-live
metric: elo_rating
model:
  id: claude-3.5-sonnet@2025-10-01
pre_registered_from: '2026-05-01T00:00:00Z'
pre_registered_to: '2026-06-01T00:00:00Z'
prml_mode: streaming
producer:
  id: falsify.dev
sample_size: 1000
seed: null
threshold: 1300
value_method: lmsys_anonymous_chat_arena_v1
version: prml/0.2
```

Streaming mode also relaxes `threshold` from v0.1's strict float64 to `int | float`, since natural streaming metrics (ELO, vote counts, request totals) are integer-valued. Integer thresholds canonicalise as plain integers under v0.2 and as `<n>.0` under v0.1; verification tools MUST pick the float-field set by inspecting the manifest's `version` field. All four reference implementations enforce this split as of 2026-05-15.

**Open question.** Is `value_method` a free-form string (interoperability through community convention) or a controlled vocabulary (smaller set of canonical methods, with a registry)?

### P-02 — Optional runner attestation field

**Problem.** A determined publisher can hash a clean evaluation set, run on a contaminated one, and report the hash of the clean set. v0.1's hash commits to *what was claimed*, not proof of *what was run*.

**Proposal.** Add an optional `runner_attestation` field that, when present, points to an out-of-band attestation of the eval execution environment. Value is an opaque URI, not interpreted by PRML itself.

**Example** (matches conformance vector TV-015 byte-for-byte):

```yaml
claim_id: 01900000-0000-7000-8000-000000000015
comparator: '>='
created_at: '2026-05-08T20:00:00Z'
dataset:
  hash: f1e2d3c4b5a6978878695a4b3c2d1e0f1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d
  id: harmbench-v1
metric: refusal_rate
model:
  id: claude-3.5-sonnet@2025-10-01
producer:
  id: falsify.dev
runner_attestation: sigstore://rekor.sigstore.dev/api/v1/log/entries/24296fb24b8ad77a
seed: 42
threshold: 0.95
version: prml/0.2
```

**Non-goal.** PRML does not specify what makes an attestation valid — that is the domain of Sigstore, in-toto, AWS Nitro, etc. PRML simply records that one was emitted.

**Open question.** Should `runner_attestation` be a single URI or a list? Multiple attestations from different layers (TEE + signing + provenance) are common in production.

### P-03 — Revocation primitive

**Problem.** A pre-registered manifest may need to be retracted (e.g. the underlying dataset is found contaminated; the model build is recalled). v0.1 has no in-spec revocation.

**Proposal.** Add an optional `revoked_at` field (RFC 3339 timestamp) and an optional `revocation_reason` field (one of `"dataset_compromised"`, `"model_recalled"`, `"author_request"`, `"other"`). A revoked manifest's hash MUST still verify; verification tools MUST surface revocation status separately from hash status.

**Example** (matches conformance vector TV-016 byte-for-byte):

```yaml
claim_id: 01900000-0000-7000-8000-000000000016
comparator: '>='
created_at: '2026-04-01T12:00:00Z'
dataset:
  hash: e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
  id: imagenet-val-2012
metric: accuracy
producer:
  id: falsify.dev
revocation_reason: dataset_compromised
revoked_at: '2026-05-15T10:00:00Z'
seed: 42
threshold: 0.92
version: prml/0.2
```

**Registry semantics.** A registry MAY mark manifests revoked. A revoked manifest's permalink remains; the badge endpoint emits `revoked` status alongside `valid`.

**Open question.** Should revocation require a separate `revocation_signature` field for non-repudiation? Adding signatures pulls in PKI choices that v0.1 deliberately avoided.

### P-04 — Conformance vector format

**Problem.** v0.1's "13 conformance vectors" are documented in prose. Future implementations cannot mechanically run them.

**Proposal.** Standardise the conformance vector format as a directory of `<vector_name>/manifest.yaml` and `<vector_name>/expected_hash.txt`. Tooling SHOULD provide a `falsify conform <impl-binary>` command that runs every vector through a target implementation and reports byte/hash match.

This is informative (non-normative) — the spec defines the format, not the test runner.

### P-05 — Patent grant in spec body

**Problem.** v0.1's patent non-assertion grant is published with the spec but appears as an appendix. CEN-CENELEC and other standards bodies have requested the grant text appear in §1 (preamble) of the spec.

**Proposal.** Move the existing grant text from Appendix C into a new §1.5 (preamble). No textual change to the grant itself. Backwards-compatible with v0.1 because the grant text is identical.

## Proposals deferred to v0.3+

The following were considered and deferred. Each is a tracking issue against `studio-11-co/falsify` with label `rfc-v0.3`.

- **Claim tree / suite manifests** (deferred — multi-metric eval batteries like HELM, Big-Bench, LMSYS Arena, LiveCodeBench need one manifest covering N (metric, dataset) pairs. v0.2 position: represent as N separate v0.1 manifests with a shared `claim_group` string. v0.3 will design a normative tree structure that hashes deterministically over its leaves.)
- **Producer cryptographic binding** (deferred — `producer` remains a plain string in v0.2 with a non-normative recommendation to anchor via git-commit SHA, Sigstore bundle, or GPG-signed manifest. v0.3 proposal: upgrade to a structured `producer: {id, key_id, signature?, sigstore_bundle?}` with SHOULD-level identity binding. Identity levels 0–4 are documented in the cookbook before v0.3 opens.)
- **Tolerance / epsilon field** (deferred — GPU floating-point non-determinism, CUDA atomic kernels, and `flash-attention`-class libraries cause sub-permille variance across hardware. A claim locked at `>= 0.9400` can FAIL on identical code, identical seed, different GPU. v0.3 proposal: optional `tolerance` numeric or `tolerance_method` enum. v0.2 explicitly does not include this — a producer who needs slack today must encode it in the threshold.)
- **Native Sigstore signing** (deferred — wraps better around than into PRML; see cookbook Pattern 11.)
- **Multi-metric manifests** (superseded by claim tree above.)
- **Granular field-level permissions** (out of scope — registries can implement.)
- **Privacy-preserving variant** (deferred — needs separate threat-model document.)

## Freeze-day editorial decisions (binding at 2026-05-22 23:59 UTC)

These are not new proposals; they are clarifications the editor is locking into the freeze record so that v0.2 readers do not relitigate them downstream.

1. **Selective non-publication remains out of scope.** A producer who locks ten manifests and publishes two is not detectable by PRML alone. v0.1 §8.1 stated this; v0.2 restates it as a freeze-day decision. Publication completeness is a registry-policy, journal-policy, or signed-execution-pipeline concern that sits on top of PRML. PRML is a per-claim commitment primitive, not a publication-integrity system.

2. **Multi-metric claims are represented as multiple manifests.** Until the v0.3 claim-tree design lands, an evaluation suite reporting ten metrics is ten v0.1/v0.2 manifests with a shared `claim_group` identifier. The hash of a suite is the ordered concatenation of leaf hashes; no normative wrapper exists in v0.2.

3. **Manifest timestamp is producer-declared. Audit value lives in the anchor timestamp.** The `timestamp` field inside the manifest is the time the producer claims to have authored the manifest. It is not externally verifiable on its own — a producer can write any ISO-8601 string. The audit-strength timestamp is the *anchor* timestamp: git commit time, registry receipt time, Sigstore/Rekor log time, arXiv submission time, DOI publication time, or CI run time. When a reviewer asks "when was this committed?", the answer is the anchor, not the manifest field. See §3.6 of v0.1.

4. **`producer` stays a plain string in v0.2 with SHOULD-level external anchoring.** A v0.2-conforming producer SHOULD anchor manifest identity to at least one externally observable artefact (git commit, registry receipt, signature) and SHOULD document the chosen identity level. The structured `producer` upgrade is v0.3 territory; v0.2 does not break the string field.

5. **P-02 `attestation_uri` distinction (contributed by Ceri John, Topeuph AI / ValiChord).** The P-02 field note distinguishes between *execution attestation* (who ran the eval and when, e.g. Sigstore as documented in Cookbook Pattern 11) and *independence attestation* (verdicts produced by parties that could not coordinate outcomes, e.g. blind commit-reveal as documented in Cookbook Pattern 13). Both address different parts of the §8.1 gap and are complementary, not alternative. The distinction surfaces during v0.2 review on Discussion #11 and lands here verbatim; Pattern 13 ships in the cookbook as a co-authored entry.

## Comment summary template

When you comment, please use this format:

```
Proposal: P-0X
Position: support / oppose / clarify
Rationale: [≤ 200 words]
Affected impl(s) (if applicable): py / js / go / rust / all
Suggested edit (optional): [diff]
```

Comments without a clear position are still useful but slow to act on.

## Editor's notes

The smallest possible change set is a feature. v0.2 is intended to be a 1-week implementation diff for any of the four reference implementations. If a proposal here cannot be implemented in that envelope, it belongs in v0.3 or later.

A list of comments received and their disposition will be published as `spec.falsify.dev/v0.2-comments` after the freeze.

— Cüneyt Öztürk, 2026-05-08 (last editorial pass: 2026-05-15)
