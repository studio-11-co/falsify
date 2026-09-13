# PRML — Pre-Registered ML Manifest Specification

**Version:** 0.1 (Draft)
**Date:** 2026-05-01
**Status:** Frozen working draft (2026-05-22) — not a finished standard
**Editor:** Cüneyt Öztürk \<hello@falsify.dev\>
**Reference Implementation:** [falsify](https://github.com/studio-11-co/falsify) (MIT)
**Canonical URL:** https://spec.falsify.dev/v0.1
**License:** [Community Specification License 1.0](./LICENSE.md) — see [Scope.md](./Scope.md) and [Notices.md](./Notices.md)

> **Correction, 2026-09-11.** §2.3.4 previously read "a registry receipt proves
> the bar was locked before the run". That overstates what a receipt establishes,
> and it contradicts both the paragraph that follows it and the threat model in
> §8.1: `created_at` defends against retroactive editing, anchoring defends
> against back-dating, and neither establishes that the evaluation ran after the
> commitment. The sentence has been narrowed to what a receipt does evidence —
> existence no later than the anchored time, and non-substitution since. No
> requirement, field, algorithm or conformance vector is affected, and no
> implementation needs to change.

> **Licence change, 2026-08-29.** This specification was previously published
> under CC BY 4.0, which grants copyright permissions only and expressly grants
> no patent rights — the wrong instrument for a document meant to be
> implemented by third parties. It is now published under the Community
> Specification License 1.0, which grants both, irrevocably, within the declared
> Scope. Copies distributed before this date remain available under CC BY 4.0;
> that grant is irrevocable and is not withdrawn here. No normative text changed
> with this licence change.

---

## Abstract

PRML defines a content-addressed serialization format for pre-registered machine
learning evaluation claims. A PRML manifest binds a metric, a numeric threshold,
a dataset content hash, and a random seed to a SHA-256 digest produced **before**
the experiment runs. After the experiment, an independent verifier recomputes the
hash, executes the evaluation against the pre-registered parameters, and emits a
deterministic verdict.

The format is designed to be implementable in any language, transmittable as a
plain text artifact, and verifiable without network access. PRML is **not** an
experiment-tracking platform; it is a primitive intended to underlie such
platforms and to satisfy regulatory audit-trail obligations under regimes
including the EU AI Act (Regulation 2024/1689) Articles 12 and 18.

---

## Status of This Memo

This document is **not** a finished standard. It is published under the Community
Specification License 1.0 by a single editor; no standards body has adopted it,
and it carries no presumption of conformity with any regulation.

**Settled.** §3 canonicalization has not changed since the freeze on 2026-05-22.
Three defect reports accepted on 2026-08-23 added rejection requirements for
invalid input; they changed no canonical byte sequence and no digest of any valid
manifest. The four reference implementations (Python, JavaScript, Go, Rust) agree
byte-for-byte on 21 conformance vectors. All four reject the 16 negative-conformance
cases that are not YAML-specific; the two implementations that parse YAML reject
all 20. The media type `application/vnd.prml+yaml` was registered with IANA on
2026-09-03; registration is not endorsement.

**Not settled.** A manifest and its digest carry no evidence of time on their own.
Only a time-anchored record — a digest countersigned by an independent timestamp
authority or entered in a public transparency log — can establish that a criteria
object existed no later than the anchored time. Even then it does not establish
that the evaluation ran afterwards: this specification does not bind a criteria
record to the execution it describes. Execution linkage is out of scope for v0.1
and is the main open gap. A time-anchored record is also silent on who held the
criteria before the run: if the party that sets the criteria and the party whose
work is assessed can communicate outside the record — the ordinary case when both
sit inside one organisation — the anchor remains valid and the assessment can
still be compromised. This specification binds bytes to a time; it does not
establish that the criteria were withheld from the party they were meant to test.
Three statements in
this document promised normative adoption "with v0.2"; v0.2 froze without them and
they are re-targeted to the v0.3 cycle (see Errata). §3 has had a formal
grammar since 2026-09-13 (§3.6), verified against all 21 conformance vectors by
an implementation written from the grammar alone. What that verification also
showed is now the open item in its place: the four reference implementations
agree byte-for-byte on the 21 conformance vectors; a wider 83-input battery
published the same day found 21 inputs, outside the vectors, on which three of
them departed from the grammar. They were corrected the same day; the one
input that exposed an unstated rule rather than a bug (a v0.2 `threshold`
spelled `1300.0`) was settled by a post-freeze clarification to the v0.2 RFC
the same day — `threshold` canonicalizes by value under v0.2. All of it now
runs in CI as a 92-vector edge suite (`spec/test-vectors/edge/`).

**Implementation status.** All four reference implementations were written by the
editor, and all public registry records to date originate with the editor. No
independent implementation is known to the editor. Independent interoperability
therefore remains unproven.

A manifest is interpreted under the rules identified by its `version` field, so
valid v0.1 manifests continue to verify under v0.1 rules as later revisions are
developed. The v0.2 RFC froze on 2026-05-22 and its formal comment window is
closed; promotion to final is deferred until external reviewers exist, and its
three open questions will not be resolved unilaterally. General feedback and
defect reports remain welcome at
`github.com/studio-11-co/falsify/discussions` or at `hello@falsify.dev`.

---

## 1. Introduction

### 1.1 Motivation

Machine learning evaluations suffer from a credibility gap that conventional
experiment-tracking tools do not close. The metric, threshold, dataset, and seed
that a team claims to have committed to *before* a training run are typically
recorded only after results are observed, if at all. Post-hoc revision of these
parameters — moving a threshold from 0.85 to 0.83, swapping a held-out split,
re-rolling a seed — is mechanically indistinguishable from honest reporting in
the absence of a cryptographic pre-commitment.

Three contemporary forces make this gap urgent:

1. **Regulatory.** The EU AI Act's logging (Article 12) and recordkeeping
   (Article 18) obligations for high-risk systems under Annex III apply from
   2 December 2027, following the deferral enacted by Regulation (EU) 2026/1744.
   High-risk AI providers must demonstrate that performance claims attached to a
   deployed model are the same claims registered prior to deployment.

   > **v0.1 erratum (2026-08-28):** this section previously stated that
   > Articles 12 and 18 obligations "enter force August 2, 2026". Regulation
   > (EU) 2026/1744 (OJ, 24 July 2026) defers Sections 1–3 of Chapter III —
   > which include both articles — to 2 December 2027 for systems classified
   > high-risk under Article 6(2) and Annex III. The original text reflected
   > the pre-Omnibus timetable and was correct when written (1 May 2026).
2. **Scientific.** Benchmark contamination, data leakage, and selective
   reporting consistently degrade the informativeness of public evaluations.
3. **Commercial.** Capability claims attached to frontier model releases are
   frequently disputed precisely because no public, tamper-evident record of the
   evaluation contract exists.

PRML proposes the smallest sufficient primitive to close this gap: a hash-bound
manifest, written before the run, verified after.

### 1.2 Conventions and Terminology

The key words **MUST**, **MUST NOT**, **REQUIRED**, **SHALL**, **SHALL NOT**,
**SHOULD**, **SHOULD NOT**, **RECOMMENDED**, **MAY**, and **OPTIONAL** in this
document are to be interpreted as described in [RFC 2119].

The following terms have specific meaning in this specification:

- **Manifest** — A document conforming to §2 that pre-registers an evaluation
  claim.
- **Canonical bytes** — The byte sequence produced by serializing a manifest
  according to §3.
- **Manifest hash** — `SHA-256(canonical bytes)`, encoded as 64 lowercase
  hexadecimal characters.
- **Producer** — The party that creates and publishes a manifest before the
  evaluation runs.
- **Verifier** — Any party (including the producer) that independently
  recomputes the manifest hash and the evaluation outcome.
- **Audit log** — The append-only sequence of manifests covering successive
  amendments to a registered claim (§6).

---

## 2. Manifest Structure

### 2.1 Required Fields

A PRML manifest is a YAML 1.2 document. Implementations **MUST** populate the
following top-level keys:

| Key | Type | Description |
|---|---|---|
| `version` | string | Spec version. **MUST** equal `"prml/0.1"` for this revision. |
| `claim_id` | string | UUIDv7 identifier for the claim. **MUST** be unique per producer. |
| `created_at` | string | RFC 3339 timestamp in UTC, second precision. |
| `metric` | string | Identifier of the metric being claimed. See §2.3.1. |
| `comparator` | string | One of `>=`, `>`, `==`, `<=`, `<`. See §5.1. |
| `threshold` | number | Real number the metric is compared against. |
| `dataset` | mapping | Identifier and content hash of the dataset. See §2.3.2. |
| `seed` | integer | Non-negative 64-bit integer. |
| `producer` | mapping | Identity of the manifest producer. See §2.3.3. |

### 2.2 Optional Fields

| Key | Type | Description |
|---|---|---|
| `metric_args` | mapping | Free-form arguments parameterizing the metric. |
| `model` | mapping | Identifier of the model under test, if known pre-run. |
| `code` | mapping | Identifier of the code (e.g., git commit) used to evaluate. |
| `prior_hash` | string | Manifest hash of the previous claim in an amendment chain (§6). |
| `notes` | string | Human-readable annotation. **MUST NOT** affect verification. |

### 2.3 Field Semantics

#### 2.3.1 `metric`

The `metric` value **MUST** be either:

- A registered identifier from the PRML Metric Registry (forthcoming, §11), or
- A URI dereferencing to a published definition.

Examples: `accuracy`, `f1_macro`, `https://example.org/metrics/calibration_ece`.

#### 2.3.2 `dataset`

```yaml
dataset:
  id: <human-readable identifier>
  hash: <hex SHA-256 of canonical dataset bytes>
  uri: <optional retrieval URI>
```

The `hash` field **MUST** be the SHA-256 digest of the dataset's canonical byte
representation. The canonical representation is dataset-format-specific and
**SHOULD** be documented in the dataset's accompanying datasheet.

#### 2.3.3 `producer`

```yaml
producer:
  id: <DNS-name, ORCID, or GitHub handle>
  signature: <optional detached PGP or minisign signature>
```

The `signature` field, when present, **MUST** be a detached signature over the
**canonical bytes** of the manifest (the same byte sequence whose SHA-256 is
the manifest hash). This matches standard cryptographic practice (Sigstore
detached signatures, minisign, PGP `--detach-sign`) and protects against
a second-preimage scenario where an adversary substitutes a different
canonical byte sequence yielding an identical hash: under hash-only signing,
such a substitution would still verify; under bytes-signing, it does not.

Verifiers MUST run canonicalization regardless (it is a prerequisite for the
hash check in §5.2 step 1), so signing over the canonical bytes adds no
redundant work. Implementations SHOULD store the signature in a sidecar
file `<claim_id>.prml.sig` alongside the existing `<claim_id>.prml.sha256`
sidecar. v0.2 normatively adopts this sidecar convention.

> **v0.1 erratum (2026-05-02):** earlier drafts of this spec instructed
> implementations to sign over the manifest hash. That recommendation is
> withdrawn. Existing v0.1 implementations that signed over the hash should
> re-sign over the canonical bytes before any regulatory submission.

#### 2.3.4 `created_at` — declared time vs. anchor time

The `created_at` field is the time the **producer declares** to have authored
the manifest. It is part of the canonical bytes and therefore part of the
hash: any change to `created_at` changes the hash. This is sufficient to
prevent a producer from retroactively editing the timestamp on a published
manifest without breaking the signature chain.

It is **not** sufficient to prove the manifest existed at the declared time.
A producer can write any RFC 3339 string into `created_at` at any moment;
the spec has no way to constrain that string against a wall clock the
producer does not control.

Audit-strength timestamps come from **anchor mechanisms** external to the
manifest:

- Git commit author/committer timestamps in a public repository,
- Registry receipt timestamps (e.g. `registry.falsify.dev` records the
  server-side wall clock at which it first observed a given manifest hash),
- RFC 3161 timestamping authorities,
- Sigstore Rekor transparency log entries,
- arXiv submission timestamps and DOI registration dates,
- CI run timestamps recorded in public workflow logs.

A verifier evaluating "when was this committed?" **MUST** treat the
`created_at` field as a producer-side claim and look to one or more anchor
mechanisms for the authoritative answer. A v0.1-conforming producer
**SHOULD** anchor every published manifest in at least one such mechanism
and document the choice. v0.2 makes this a normative SHOULD; v0.1 leaves
the choice informative.

**These anchor mechanisms are not equally strong** *(updated 2026-07-11)*.
Git commit timestamps, RFC 3161 timestamping authorities, and Sigstore
Rekor entries provide *independent non-repudiation*: a third party, not the
producer, vouches for the time, and the record cannot be silently
withdrawn. `registry.falsify.dev` sits in between. Since June 2026 its
receipts are Ed25519-signed over the manifest hash and the server-side
timestamp (public key at `registry.falsify.dev/pubkey`), which gives
non-repudiation of issuance: the operator cannot later deny having issued a
receipt. Since 2026-07-11 the registry validates PRML manifests at commit
time and stores the full manifest rather than a preview. Since 2026-07-12
every receipt is additionally countersigned by an independent RFC 3161
timestamp authority (timestamp.sigstore.dev): the token, served raw at
`registry.falsify.dev/<hash>.tsr`, signs the manifest hash with the TSA's
key and verifies offline with OpenSSL against the TSA's published chain,
so the *time* claim no longer rests on the registry operator alone.
(Records committed before that date were backfilled; their token time is
later than their receipt time, and the permalink says so.) Since the same date,
records that store their full manifest are also mirrored to Sigstore's
public Rekor v2 transparency log (the per-record inclusion proof is served
at `registry.falsify.dev/<hash>.rekor`), which adds append-only,
non-equivocation evidence for those records; the registry itself remains a
signed store, not a log. It is useful for in-browser verification
and as corroboration, but it **SHOULD NOT** be relied on as the sole
audit-grade anchor for high-risk or regulatory use; select at least one
additional independent mechanism from the list above. In every case a
registry receipt evidences that a specific criteria object existed no later
than the anchored time and is unchanged since. It does **not** evidence that
the evaluation ran afterwards — establishing that order requires a separate
execution-side record, dated independently of this one — and it never proves
the result.

This distinction matters for §8.1 threat-model analysis: the
threat that `created_at` defends against is the producer **retroactively
editing** a published manifest. The threat that anchoring defends against is
the producer **back-dating** a manifest that was authored after the fact.
The two are different and require different mechanisms.

There is a third limit, and it is the boundary of what any receipt can carry.
Anchoring establishes that the committed bytes existed **no later than** the
anchor time and have not changed since. That the evaluation ran *after* that
point — and therefore that the bar preceded the result — follows from using the
mechanism as intended: anchor first, then run. A receipt encountered in
isolation, with no independent evidence of when the run began, bounds the
commitment in time but does not by itself order it against the run.

---

## 3. Canonical Serialization

### 3.1 YAML Subset

A PRML manifest **MUST** be expressible in the following YAML subset:

- Block-style mappings only (no flow-style).
- Plain scalars, double-quoted scalars, and integers.
- No anchors, aliases, or tags beyond `!!str`, `!!int`, `!!float`.
- UTF-8 throughout; string scalars and keys are restricted to the portable character set of §3.4.

### 3.2 Key Ordering

For canonicalization, all mappings **MUST** be reserialized with keys in
lexicographic byte order. Nested mappings are ordered recursively.

### 3.2.1 Duplicate Keys

A mapping **MUST NOT** contain the same key twice, at any nesting level. Common
YAML and JSON parsers resolve a repeated key last-wins with no diagnostic, which
means the manifest a human reads and the manifest the hash binds can carry
different values for the same field — a tamper channel inside a tamper-evident
format. RFC 7493 (I-JSON) §2.3 prohibits duplicate names for the same reason. An
implementation **MUST** detect duplicates in the input document, before or during
parsing, and reject the manifest with exit code `2`. Detecting them only after
parsing is insufficient: by then the duplicate has already been discarded.

### 3.3 Whitespace and Encoding

- Canonical output **MUST** be UTF-8 encoded.
- Indentation **MUST** be exactly two spaces per level.
- Each key-value line **MUST** terminate with a single LF (`0x0A`).
- The canonical byte sequence **MUST** end with a single LF.
- Trailing whitespace is **PROHIBITED**.
- Comments are **PROHIBITED** in canonical form.

A reference canonicalizer is provided by the falsify implementation and produces
output byte-equivalent to the rules above for any conforming input.

### 3.4 Portable Character Set

To guarantee byte-identical canonicalization across implementations, every
string scalar and every mapping key **MUST NOT** contain any of the following
code points:

- U+0000–U+001F (C0 control characters)
- U+007F (DELETE) and U+0080–U+009F (C1 control characters)
- U+2028 (LINE SEPARATOR) and U+2029 (PARAGRAPH SEPARATOR)
- U+FEFF (BYTE ORDER MARK / ZERO WIDTH NO-BREAK SPACE)

These code points serialize ambiguously or invisibly and would let two
visually identical manifests hash differently. A manifest containing any of
them **MUST** be rejected — it **MUST NOT** be locked or hashed — and the
implementation **MUST** exit with code `2` (bad input). The control-character
vectors in the reject suite (Appendix B) enumerate this class normatively.

Additionally, every string scalar and every mapping key **MUST** be in Unicode
Normalization Form C (NFC). The same text in NFC and in NFD is identical to a
reader and different to SHA-256, so a claim authored on a platform that composes
differently would lock to a different hash than the same claim authored
elsewhere. A manifest containing a non-NFC string **MUST** be rejected with exit
code `2`; an implementation **MUST NOT** normalize it silently, because doing so
would change the bytes the author believes they locked. All other UTF-8 is
permitted in string values.

### 3.5 Numeric Rendering

`threshold` is a float64 (§2.3). An integer-valued threshold **MUST**
canonicalize as a float — `1` renders as `1.0` — so that `1` and `1.0` produce
the same hash. `seed` is an integer and renders with no decimal point.

`threshold` **MUST** be finite. The IEEE 754 special values — positive and
negative infinity and NaN, spelled `.inf`, `-.inf` and `.nan` in YAML — are
**PROHIBITED**. Such a manifest locks and verifies cleanly while asserting
nothing: every observation satisfies `<= .inf`, and no observation satisfies any
comparison against `.nan`. The result is a bar that no experiment can inform,
which defeats the purpose of fixing one in advance. A manifest whose `threshold`
is non-finite **MUST** be rejected with exit code `2`.

Floating-point values **MUST** be rendered in the canonical decimal form: the
shortest decimal that round-trips to the same float64, with very small or very
large magnitudes in normalized scientific notation (for example, `0.000001`
renders as `1.0e-06`). The exact rule — which magnitudes take which notation,
the mantissa and exponent spelling — is constraint C4 of the formal grammar
(§3.6); the reference canonicalizer (§3.3, §10) is a conforming implementation
of it. The per-language canonicalization-portability analysis records how each
reference implementation reproduces the rule and where, outside the conformance
vectors, one of them does not (finding of 2026-09-13).

### 3.6 Formal Grammar

The canonical byte sequence is specified by the ABNF grammar in
[`spec/grammar/prml-canonical.abnf`](grammar/prml-canonical.abnf) together with
the constraints C1–C7 stated in [`spec/grammar/README.md`](grammar/README.md):
depth (C1), key order (C2), uniqueness (C3), float rendering (C4), the
plain-scalar predicate (C5), which production a value takes (C6), and block
sequences (C7, informative). The grammar and constraints C1–C6 are
**normative**. The reference canonicalizer is one conforming implementation of
them, not their definition. An implementation that satisfies the grammar and
C1–C6 produces, for every conformance vector in Appendix B, exactly the
published canonical bytes and hash.

The grammar was added on 2026-09-13 and verified in both directions before
publication: an emitter and a recogniser written from the grammar alone,
without the reference canonicalizer or its YAML library
([`spec/grammar/check_grammar.py`](grammar/check_grammar.py)), reproduce all
21 conformance vectors byte-for-byte and reject sixteen deliberately malformed
canonical texts. Publishing the grammar changes no canonical byte sequence and
no digest of any valid manifest; it states what the reference canonicalizer
already emits.

Stating the plain-scalar predicate exactly also made its edges testable. A
battery of 83 inputs built for that purpose
([`spec/grammar/candidate-vectors-2026-09-13.json`](grammar/candidate-vectors-2026-09-13.json))
showed that three of the four reference implementations departed from the
grammar on 21 inputs, none of which is covered by a conformance vector (README,
"Divergences"). The three implementations were corrected the same day to the
predicate and the float rule as stated. The one input that was not a bug but an
unstated rule — a v0.2 manifest whose `threshold` is spelled `1300.0`, which a
JavaScript JSON or YAML parser cannot tell from `1300` — was settled the same
day by a post-freeze clarification to the v0.2 RFC: under `prml/0.2`,
`threshold` canonicalizes **by value**, an integral value below 2^53 as an
integer and anything else as a float (C6). All 83 inputs plus ten vectors
pinning that rule's boundaries now form the **edge suite**
([`spec/test-vectors/edge/`](test-vectors/edge/), 92 vectors), which the
multi-language CI runs for all four implementations alongside Appendix B.

An implementer starting from this specification alone should begin with
[`IMPLEMENTERS-GUIDE.md`](IMPLEMENTERS-GUIDE.md): where each rule is stated, the
corpus to check against, the commands, and the errors the reference
implementations themselves made.

---

## 4. Hash Algorithm

The manifest hash **MUST** be computed as:

```
hash = lowercase_hex(SHA-256(canonical_bytes))
```

Implementations **MUST NOT** strip a trailing newline, normalize line endings to
CRLF, or otherwise alter `canonical_bytes` before hashing.

The hash **SHOULD** be published alongside the manifest in a sidecar file
named `<claim_id>.prml.sha256`.

---

## 5. Verification Semantics

### 5.1 Comparison Operators

| `comparator` | Pass condition |
|---|---|
| `>=` | observed ≥ threshold |
| `>` | observed > threshold |
| `==` | abs(observed - threshold) < tolerance |
| `<=` | observed ≤ threshold |
| `<` | observed < threshold |

The `==` comparator's tolerance defaults to `1e-9`. Producers **MAY** override
this by setting `metric_args.tolerance`.

### 5.2 Pass/Fail Determination

A verifier **MUST**:

1. Recompute the manifest hash from `canonical_bytes` and verify it matches the
   published hash.
2. If the verifier holds the dataset content the producer hashed, recompute
   its digest and verify it matches `dataset.hash`. PRML v0.1 does not
   standardize a dataset preimage or hashing procedure, so `dataset.hash` is a
   producer-declared content digest; a verifier without the exact bytes (or
   without the producer's documented procedure) cannot recompute it, and for
   dynamically generated eval data it may not be recomputable at all. The
   reference CLI implements the single-file case via `verify --dataset <path>`.
3. Execute the evaluation using the manifest's `metric`, `metric_args`, `seed`,
   and dataset.
4. Apply the comparator from §5.1.
5. Emit a verdict per §7.

### 5.3 Tampering Detection

If the recomputed manifest hash does not match the published hash, the verifier
**MUST** abort verification and **MUST NOT** emit a Pass or Fail verdict.
Implementations **MUST** signal tampering distinctly from evaluation failure
(see §7).

---

## 6. Amendment Protocol

PRML treats every claim as immutable once hashed. Honest revision is supported
through an explicit, append-only amendment chain.

### 6.1 Forward-Only Audit Log

A producer who needs to change any field of a previously-registered claim
**MUST** create a new manifest whose `prior_hash` field equals the manifest
hash of the previous claim. The new manifest **MUST** retain the `claim_id` of
the previous claim.

The full sequence of manifests sharing a `claim_id`, ordered by `created_at`
and verified by the `prior_hash` chain, constitutes the audit log for that
claim.

### 6.2 Amendment Semantics

- The previous manifest is **NOT** deleted, overwritten, or revoked.
- Verifiers **MUST** treat the latest manifest in the chain as the operative
  one, but **MUST** also expose the full chain when requested.
- Hash-equality of two claims with identical content but different `created_at`
  values **MUST NOT** occur; canonicalization includes the timestamp.

### 6.3 Amendment Chain Hash

An aggregate identifier for the full chain, suitable for public posting, is:

```
chain_hash = SHA-256(concat(canonical_bytes_1, canonical_bytes_2, ..., canonical_bytes_n))
```

where the manifests are concatenated in `created_at` order.

---

## 7. Exit Code Specification

Reference implementations **MUST** signal verification outcomes via the
following exit codes:

| Code | Meaning |
|---|---|
| `0` | Pass — manifest verified, evaluation satisfies comparator. |
| `10` | Fail — manifest verified, evaluation does not satisfy comparator. |
| `3` | Tampered — manifest hash mismatch, verification aborted. |
| `11` | Guard violation — manifest is well-formed but a producer-declared invariant (e.g., dataset-hash mismatch, seed out of range) failed. |
| `2` | Usage error — invalid command-line arguments or unreadable manifest. |
| `1` | Unspecified runtime error. |

Codes other than `0`, `1`, `2`, `3`, `10`, `11` are **RESERVED**.

---

## 8. Security Considerations

### 8.1 Threat Model

PRML protects against **silent post-hoc revision** of a registered claim. It
does **NOT** protect against:

- A producer who never publishes the manifest at all.
- A producer who publishes a manifest privately, runs the evaluation, then
  publishes only on Pass (selective publication).
- A producer colluding with the dataset host to alter dataset content while
  preserving its declared hash (broken hash function).
- A producer signing a manifest with a key the verifier cannot validate.

Mitigations require external mechanisms: timestamping services (RFC 3161),
public manifest registries, or signed dataset hosts.

> **v0.1 erratum on selective publication (2026-05-02).** For regulatory use
> — particularly EU AI Act Annex III high-risk system audits — selective
> publication is the most likely real-world adversary, not the theoretical
> ones above. The cryptographic protocol is satisfied by a producer who
> publishes only Pass results; the regulatory purpose is not. v0.1
> implementations used in compliance contexts MUST adopt one of the
> following deployment-level mitigations, none of which v0.1 enforces but
> all of which are compatible with the v0.1 manifest format:
>
> 1. **Publish-before-run discipline.** The manifest URL is committed to a
>    public registry (a Git tag, an RFC 3161 timestamping authority, or an
>    immutable S3 object with public-read) **before** the evaluation runs,
>    not after. The registrar's timestamp becomes the publication-time
>    proof; the manifest itself remains regulator-verifiable offline.
>
> 2. **Sequential `claim_id` allocation.** A producer's `claim_id`
>    sequence is published as a monotonic chain (each `claim_id` is the
>    successor of the previous, regardless of outcome). A regulator can
>    detect missing entries in the sequence and demand explanation.
>
> 3. **External pre-registration anchor.** The manifest hash is committed
>    to a third-party pre-registration registry (OSF, ClinicalTrials.gov
>    pattern adapted, or an in-house immutable log) before any evaluation.
>    The anchor is what the regulator verifies; the manifest is the
>    provenance.
>
> v0.2 will normatively adopt option (3) for the `producer.tier:
> high-risk` profile. v0.1 deployments choosing not to adopt one of these
> three mitigations are NOT suitable for EU AI Act Article 12 evidence
> submission and the producer SHOULD declare so in their accompanying
> conformity-assessment documentation.

### 8.2 Hash Algorithm Agility

This revision fixes SHA-256 as the hash algorithm. Future revisions **MAY**
introduce algorithm agility via a `hash_algorithm` field defaulting to
`sha-256`. Verifiers conforming to v0.1 **MUST** reject manifests declaring any
other algorithm.

### 8.3 Canonical Form Attacks

A producer who serializes a manifest non-canonically and publishes the
non-canonical hash is detectable: any verifier recanonicalizing the manifest
will compute a different hash and emit Tampered (exit 3). This places
canonicalization correctness on the verifier, not the trust path.

---

## 9. Compliance Mapping (Informative)

This section is non-normative.

### 9.1 EU AI Act (Regulation 2024/1689)

| Article | Obligation | PRML coverage |
|---|---|---|
| 12 | Automatic recording of events over the system's lifetime | A PRML chain is the record of evaluation events with a tamper-evident hash chain. |
| 18 | Documentation retention for 10 years post-market | PRML manifests are plain text artifacts <1 KB; retention is trivial. |
| 17 | Quality management system covering performance | Pre-registered thresholds satisfy the "objective performance metric" requirement. |
| 50 | Transparency obligations for deployers | Public manifest hashes provide the receipt deployers need. |

### 9.2 NIST AI Risk Management Framework

PRML directly supports the **MEASURE** and **MANAGE** functions: pre-registered
manifests establish the metric framework before deployment and provide the
evidence trail for ongoing monitoring.

### 9.3 ISO/IEC 42001 (AI Management System)

PRML manifests are admissible as objective evidence under §8.4 (Operational
Planning and Control) of ISO/IEC 42001:2023.

---

## 10. Reference Implementation

The [falsify](https://github.com/studio-11-co/falsify) project provides a
reference implementation in Python. Conformance to this specification is
defined as:

1. Producing canonical bytes byte-equivalent to the falsify reference for the
   PRML test vector suite (Appendix B).
2. Computing manifest hashes byte-equivalent to the reference.
3. Emitting exit codes per §7 for the test vector suite.

A conformance test harness will be published with v0.2.

---

## 11. IANA Considerations

The media type `application/vnd.prml+yaml` is registered with IANA in the
vendor tree (registered 2026-09-03; entry at
https://www.iana.org/assignments/media-types/application/vnd.prml+yaml).
The registration records the file extensions `.prml` and `.prml.yaml`,
encoding `binary` (UTF-8, NFC, no BOM; transports MUST NOT re-encode), and
the security and interoperability considerations of sections 5 and 8.

The sidecar extension `.prml.sha256` is a convention of this specification
and is not part of the media type registration.

A PRML Metric Registry will be established with v0.2.

---

## 12. References

### Normative

- [RFC 2119] Bradner, S., "Key words for use in RFCs to Indicate Requirement Levels", March 1997.
- [RFC 3339] Klyne, G., "Date and Time on the Internet: Timestamps", July 2002.
- [FIPS 180-4] NIST, "Secure Hash Standard", August 2015.
- [YAML 1.2] YAML Specification, October 2009.

### Informative

- [EU 2024/1689] Regulation (EU) 2024/1689 (AI Act), June 2024.
- [NIST AI RMF] NIST AI Risk Management Framework 1.0, January 2023.
- [ISO 42001] ISO/IEC 42001:2023, AI Management System.
- [Gelman 2018] Gelman, A. & Loken, E., "The garden of forking paths".
- [Ioannidis 2005] Ioannidis, J., "Why most published research findings are false".

---

## Appendix A — Minimal Example Manifest

```yaml
version: "prml/0.1"
claim_id: "01900000-0000-7000-8000-000000000000"
created_at: "2026-05-01T12:00:00Z"
metric: "accuracy"
comparator: ">="
threshold: 0.85
dataset:
  id: "imagenet-val-2012"
  hash: "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
seed: 42
producer:
  id: "falsify.dev"
```

Canonical bytes hash (verify with the reference implementation — `falsify hash`):

```
47f9956b3b9c495b3bf03b67398f54d0aa2133a2faf9b0522a9efa90bb109466
```

---

## Appendix B — Test Vectors

A conformance suite of **12 test vectors** is published alongside this
specification at:

> `https://github.com/studio-11-co/falsify/tree/main/spec/test-vectors/v0.1/`

Each vector defines:

1. An **input manifest** (logical YAML mapping; key order irrelevant).
2. The **canonical UTF-8 byte sequence** the canonicalizer MUST produce.
3. The **lowercase hex SHA-256** of those bytes.

An implementation conforms to PRML v0.1 if and only if it reproduces all
13 vectors exactly. The vectors cover:

| ID | Property exercised |
|---|---|
| TV-001 | Minimal valid manifest (matches Appendix A) |
| TV-002 | Key-ordering invariance — random insertion order produces same hash |
| TV-003 | Single-bit-of-content sensitivity — `0.85` vs `0.86` produces different hash |
| TV-004 | Optional fields populated (`model.id`, `model.hash`, `dataset.uri`) |
| TV-005 | Unicode in `producer.id` (UTF-8 byte handling) |
| TV-006 | Maximum seed value (`2⁶⁴ - 1`) |
| TV-007 | Minimum seed value (`0`) |
| TV-008 | Equality comparator (`==` with integer-valued threshold) |
| TV-009 | Amendment with `prior_hash` linkage to TV-001 |
| TV-010 | `pass@k` metric with model fields |
| TV-011 | AUROC with strict-greater comparator (`>`) |
| TV-012 | Regression metric (`mae`) with `<=` minimization |

Vectors are regeneratable via
`python3 spec/test-vectors/v0.1/generate.py`. Once v0.1 is frozen
(2026-05-22), the vectors and their hashes are immutable. Any change
requires a v0.2 spec bump.

Conformance is enforceable via the falsify reference test suite
(`tests/test_prml_vectors.py`); CI fails if any vector diverges.

---

## Change Log

- **v0.1 (2026-05-01)** — Initial public draft.
- **v0.1 (2026-05-01)** — Test vector suite (13 vectors) published in
  `spec/test-vectors/v0.1/`; Appendix B finalized.
- **v0.1 errata (2026-07-11):** three v0.2 forward-promises corrected
  below. Documentation only; zero normative changes, no effect on
  canonicalization or on any published hash.
- **v0.1 errata (2026-08-23), TECHNICAL:** three defect reports closed with
  new normative constraints (§3.2.1, §3.4, §3.5). Unlike the 2026-07-11
  errata, these **do** change conformance: they narrow what an implementation
  may accept. No canonical rendering changes and **no already-published hash
  changes** — every manifest that was valid and free of these defects hashes
  exactly as before.

> **v0.1 erratum (2026-07-11): v0.2 forward-promises.** Three statements in
> this document promised normative adoption "with v0.2". The v0.2 RFC froze
> on 2026-05-22 without adopting them. Each item quotes the original
> wording and states the correction. Nothing else in this document changes.
>
> 1. §2.3.1 / §11 promised: "A PRML Metric Registry will be established
>    with v0.2." Correction: deferred; re-targeted to the v0.3 cycle. Until
>    then, the URI option in §2.3.1 is the only registered-identifier path.
>
> 2. §2.3.3 promised: "v0.2 normatively adopts this sidecar convention"
>    (the `.prml.sig` signature sidecar). Correction: deferred; re-targeted
>    to the v0.3 cycle. The sidecar remains a SHOULD-level recommendation.
>
> 3. §8.1 promised: "v0.2 will normatively adopt option (3) for the
>    `producer.tier: high-risk` profile." Correction: deferred; re-targeted
>    to the v0.3 cycle. The three §8.1 deployment-level mitigations remain
>    available and recommended; none is normatively required by v0.2.

> **v0.1 erratum (2026-08-23): three defect reports, TECHNICAL.** Each was
> reproduced against the reference implementation before being written up; each
> narrows the set of manifests an implementation may accept. Manifests already
> published that do not exhibit these defects are unaffected, and no canonical
> byte sequence or hash changes.
>
> 1. **Non-finite `threshold` accepted (§3.5).** `comparator: "<="` with
>    `threshold: .inf` locked cleanly and verified `PASS` (exit `0`) against an
>    observation of `0.01`. The manifest was cryptographically sound and
>    epistemically empty. Correction: `threshold` MUST be finite; `.inf`,
>    `-.inf` and `.nan` MUST be rejected with exit `2`.
>
> 2. **Duplicate keys silently resolved last-wins (§3.2.1).** A manifest with
>    `metric` twice parsed without a diagnostic, so the value a reader saw and
>    the value the hash bound differed. Correction: duplicates MUST be detected
>    in the input document and rejected with exit `2`.
>
> 3. **Unicode normalization unconstrained (§3.4).** The same producer name in
>    NFC and NFD both validated and produced different hashes, breaking
>    reproducibility for honest users moving a manifest between platforms.
>    Correction: all strings and keys MUST be NFC; non-NFC input MUST be
>    rejected, never silently normalized.
>
> Reject-suite vectors RJ-015 through RJ-020 (Appendix B) enumerate these three
> classes normatively, through both the YAML and the JSON door.

> **v0.1 erratum (2026-09-13): formal grammar published, EDITORIAL, with one
> finding.** §3.6 is added and points to `spec/grammar/`. The grammar was derived
> from the observable behaviour of the reference canonicalizer and verified in
> both directions on all 21 conformance vectors by an implementation written
> from the grammar alone; it changes no canonical byte sequence and no digest.
> Two consequences are recorded rather than made silently:
>
> 1. **§3.5 called the reference canonicalizer "normative for this rendering".**
>    That sentence is replaced. The grammar's constraint C4 is normative and the
>    canonicalizer conforms to it. A specification that makes a program
>    normative is documentation of that program.
>
> 2. **The exact plain-scalar predicate (C5) exposed 21 inputs, none covered by a
>    conformance vector, on which the JavaScript, Go and Rust reference
>    implementations do not reproduce the reference bytes:** over-quoting `?x`,
>    `y`, `1e5`; under-quoting `<<`, `1:30`, `1_000`, a lone `-`; Rust rendering
>    a `threshold` of 1e-05 as `0.00001`; JavaScript unable to distinguish
>    `1300.0` from `1300` under v0.2. The first three classes were corrected the
>    same day. The last was not a defect but a rule the v0.2 RFC had never
>    stated, and was settled the same day by a post-freeze clarification to that
>    RFC: under `prml/0.2`, `threshold` canonicalizes by value — integral and
>    below 2^53 as an integer, otherwise as a float. No published digest changes
>    (no vector spelled an integral threshold as a float). The 83 inputs plus ten
>    boundary vectors for that rule now run in CI as the edge suite
>    (`spec/test-vectors/edge/`, 92 vectors); the pre-correction measurement is
>    kept as a dated snapshot in `spec/grammar/candidate-vectors-2026-09-13.json`.
>    The claim this document makes — agreement on the 21 vectors of Appendix B —
>    is unchanged and was re-verified the same day; the four implementations now
>    also agree on all 92 edge vectors.

---

*Editor's note: This document is intended to be readable, implementable, and
boring. Excitement is reserved for what gets built on top of it.*
