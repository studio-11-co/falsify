# PRML Execution Linkage — `prml-linkage/0`

**Status:** Draft 0 (non-normative). Open for input; nothing here is frozen.
**Editor:** Cüneyt Öztürk · hello@falsify.dev · Falsify OÜ (reg. 17574308, Estonia)
**Supersedes:** `docs/execution-linkage-draft.md` (strawman, 2026-07-31)
**License:** CC BY 4.0
**Reference implementations:** `falsify_linkage.py` (Python) · `impl/js/linkage.js` (also `falsify-js` npm ≥ 0.1.11) · `impl/go/linkage.go` · `impl/rust/src/linkage.rs` — byte-parity across all four asserted by `tests/test_linkage_parity.py`. Adapter precedent: `mlflow-falsify >= 0.3.0`.

---

## 1. Problem

A PRML receipt proves **no-later-than existence** of the evaluation bar: the
manifest hash was anchored at time T, so the bar cannot have been written
after a result observed later than T. It does **not** prove the evaluation
had not already run before T. A producer could run the eval first, observe
the result, then lock a bar the result clears.

This gap was named independently by the Andes interoperability assessment
(finding 3) and by RFC v0.2 review (P-02 discussion). Closing it requires
linking a separately evidenced **execution** to the prior receipt, so that
the order *lock → run → result* is itself evidenced.

## 2. Design

Two records, chained:

1. A **start record** is created at run start. It names the locked manifest
   hash and the run's identity, and contains **no result**. Its hash is
   computed immediately and — at the stronger tier — anchored externally
   (registry, RFC 3161, transparency log) before the run proceeds.
2. A **final record** is created at run end. It embeds the start record's
   hash (`start_hash`), adds the `result` block, and nothing else. Its hash
   can be anchored again.

Because the final record chains to the start record, and the start record
predates the result by construction, a verifier can check the claimed
chronology *lock ≤ start < finish* against independent anchor timestamps
wherever they exist.

## 3. Record format

Serialization is YAML, canonicalized with **the same rules as PRML v0.1
manifests**: `sort_keys`, block style, unicode allowed, width 4096, LF.
The record hash is the SHA-256 of the canonical UTF-8 bytes.

### 3.1 Start record

```yaml
linkage_version: prml-linkage/0
manifest_hash: "<sha256 hex of the locked PRML manifest>"
receipt: "<registry receipt URL, or null>"
run:
  id: "<runner-native run identifier>"
  started_at: "<RFC 3339 UTC, recorded at start>"
  environment: "<free-form runner fingerprint>"
  model_version: "<as pinned in the manifest, or null>"
  dataset_hash: "<sha256 hex; MUST equal manifest dataset.hash>"
```

### 3.2 Final record

The final record is the start record plus exactly two additions:

```yaml
# ... all start-record fields, byte-identical values ...
start_hash: "<sha256 hex of the canonical start record>"
result:
  observed: <number>
  digest: "<sha256 hex of the raw result artifact>"
  exit_code: <0 | 3 | 10 | 11>     # falsify verdict exit codes
  finished_at: "<RFC 3339 UTC>"
```

`exit_code` reuses the falsify CLI convention: `0` pass, `10` fail,
`3` hash mismatch, `11` guard violation.

**Float rule.** `result.observed` is a float64 field, with the same
cross-language rendering rule as v0.1 `threshold`: an integer-valued
`observed` canonicalizes with an explicit `.0` suffix (`1.0`, never `1`).
Implementations MUST coerce `observed` to float before canonicalization so
that Python, JavaScript, Go and Rust produce identical bytes.

## 4. Verification algorithm

Given a final record `F`, optionally the start record `S` and the locked
manifest `M`, a verifier checks in order:

| # | Check | Failure code |
|---|---|---|
| 1 | `F` parses; `linkage_version == "prml-linkage/0"`; required fields present, no unknown top-level fields | `malformed` |
| 2 | If `S` given: `hash(S) == F.start_hash` | `chain-broken` |
| 3 | If `S` given: `S` equals `F` minus `start_hash`/`result`, byte-compared field-wise | `chain-broken` |
| 4 | `F.run.started_at < F.result.finished_at` | `chronology` |
| 5 | If `M` given: `F.manifest_hash == hash(M)` | `manifest-mismatch` |
| 6 | If `M` given: `F.run.dataset_hash == M.dataset.hash` | `dataset-mismatch` |
| 7 | If `M` given: recompute verdict from `F.result.observed` against `M.threshold`/`M.comparator`; must match `F.result.exit_code` (0/10) | `verdict-mismatch` |
| 8 | If anchor timestamps known (receipt, RFC 3161, log inclusion): `anchor(M) ≤ anchor(S) ≤ F.run.started_at` within declared tolerance | `chronology` |

A record that passes 1–7 without `S`/`M` verifies at **integrity** level
only; the caller is told which checks were skipped. Verification is
offline-first: no check requires network access.

## 5. Strength tiers

This resolves the strawman's open question 1 (mandatory vs optional
pre-commitment) as **tiers, not mandates**:

- **Tier L1 — declared.** Only a final record exists. The runner attests
  its own chronology. Catches casual post-hoc reordering; a premeditated
  fabricator defeats it.
- **Tier L2 — chained.** Start record exists and hashes into the final
  record. Fabrication now requires constructing the start record before
  the result — i.e. premeditation before every run.
- **Tier L3 — anchored.** The start record's hash is externally anchored
  (registry receipt, RFC 3161 countersignature, transparency log) before
  the run completes. Chronology is now checkable against third-party
  clocks. This is the tier the falsify registry will serve.

Verifiers report the tier they could actually establish, never a higher
one.

## 6. Honest limits

The runner attests its own start time; without a trusted execution
environment this is process evidence, not cryptographic proof. L3 narrows
the forgery window to "fabricated before the anchor", but a producer who
runs the eval, observes the result, and only then begins the lock → start
→ finish ceremony is not detectable by linkage alone — that scenario is
constrained by anchor density (how often you lock) and by §8.1's existing
honesty about selective publication. Linkage raises the cost of the
"already ran" attack from casual to premeditated; it does not make it
impossible.

## 7. Open questions (carried, narrowed)

1. ~~Mandatory vs optional start pre-commitment~~ — resolved as tiers (§5).
2. Runner `environment` fingerprint: stays free-form in draft 0. A
   SHOULD-level recommended vocabulary (os, accelerator, framework
   versions) is a candidate for draft 1 once two independent runners
   exist.
3. ~~Registry residence~~ — first implementation exists (2026-08-13):
   registry.falsify.dev `/commit` recognizes valid linkage records and
   labels them `kind: "linkage"` (form `start`/`final`), with its existing
   RFC 3161 + Rekor anchors providing tier L3 for committed start records.
   Whether this becomes normative registry behavior (vs adapter-local
   storage) stays open until a second registry exists.

## 8. Relationship to RFC v0.2 P-02

P-02's `runner_attestation` URI records that an out-of-band execution
attestation *exists*. Linkage is one concrete thing such a URI can point
to. The two compose: a manifest may carry `runner_attestation` pointing at
an anchored final linkage record. Neither depends on the other, and the
freeze-day distinction between execution attestation and independence
attestation (freeze decision 5, contributed by Ceri John) applies
unchanged: linkage is execution-side evidence and says nothing about
verdict independence.
