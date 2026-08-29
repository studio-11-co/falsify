# PRML v0.1 Test Vectors

**Specification:** [PRML v0.1](https://spec.falsify.dev/v0.1)
**Reference implementation:** [`falsify`](https://github.com/studio-11-co/falsify) — `_canonicalize()` in `falsify.py`
**Generated:** 2026-05-01
**Editor:** Cüneyt Öztürk — `hello@falsify.dev`
**License:** Community Specification License 1.0

---

## Purpose

These test vectors define the canonical-bytes-and-hash mapping for PRML v0.1 manifests. An implementation conforms to the specification if and only if, for each test vector, it produces:

1. The exact canonical UTF-8 byte sequence shown under **Canonical bytes**, and
2. The exact lowercase hex SHA-256 digest shown under **Expected hash**.

Implementations in languages other than Python (Rust, Go, TypeScript, etc.) MUST reproduce all 13 vectors. Discrepancies indicate either an implementation bug or a specification ambiguity that v0.2 must resolve.

---

## Index

| ID | Title | Hash (first 12 chars) |
|---|---|---|
| `TV-001` | Minimal valid manifest | `1a3466cc08ee` |
| `TV-002` | Key ordering — random insertion order | `1a3466cc08ee` |
| `TV-003` | Threshold mutation — single field change | `b96b5b8d613e` |
| `TV-004` | Optional fields — model and dataset.uri populated | `609308e259dc` |
| `TV-005` | Unicode in producer.id | `6cf48a868f8f` |
| `TV-006` | Maximum seed value | `57c71c567e0c` |
| `TV-007` | Minimum seed value | `766d6ca6ee06` |
| `TV-008` | Equality comparator | `fc2bf632dfb1` |
| `TV-009` | Amendment manifest with prior_hash | `29c60f7ccfb1` |
| `TV-010` | pass@k metric for code generation | `60f8eb35dd21` |
| `TV-011` | AUROC with low threshold | `91104f15ee95` |
| `TV-012` | MAE for regression | `ec1d18427451` |
| `TV-013` | Integer-valued threshold | `cb9683ce70f5` |

---

## TV-001 — Minimal valid manifest

The smallest manifest that satisfies all required fields. Matches Appendix A of the PRML v0.1 specification.

**Input (logical YAML, key order is irrelevant):**

```yaml
version: prml/0.1
claim_id: 01900000-0000-7000-8000-000000000000
created_at: '2026-05-01T12:00:00Z'
metric: accuracy
comparator: '>='
threshold: 0.85
dataset:
  id: imagenet-val-2012
  hash: e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
seed: 42
producer:
  id: studio-11.co
```

**Canonical bytes (UTF-8, exact):**

```yaml
claim_id: 01900000-0000-7000-8000-000000000000
comparator: '>='
created_at: '2026-05-01T12:00:00Z'
dataset:
  hash: e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
  id: imagenet-val-2012
metric: accuracy
producer:
  id: studio-11.co
seed: 42
threshold: 0.85
version: prml/0.1
```

**Expected hash (lowercase hex SHA-256 of canonical bytes):**

```
1a3466cc08ee7fb60a726ea1c4db6ecf48a9f847b9b7523bfb54b2ffaefee546
```

---

## TV-002 — Key ordering — random insertion order

Same fields as TV-001 but constructed with reverse insertion order. Hash MUST equal TV-001 because canonicalization sorts keys lexicographically.

**Input (logical YAML, key order is irrelevant):**

```yaml
seed: 42
producer:
  id: studio-11.co
version: prml/0.1
threshold: 0.85
metric: accuracy
dataset:
  hash: e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
  id: imagenet-val-2012
created_at: '2026-05-01T12:00:00Z'
comparator: '>='
claim_id: 01900000-0000-7000-8000-000000000000
```

**Canonical bytes (UTF-8, exact):**

```yaml
claim_id: 01900000-0000-7000-8000-000000000000
comparator: '>='
created_at: '2026-05-01T12:00:00Z'
dataset:
  hash: e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
  id: imagenet-val-2012
metric: accuracy
producer:
  id: studio-11.co
seed: 42
threshold: 0.85
version: prml/0.1
```

**Expected hash (lowercase hex SHA-256 of canonical bytes):**

```
1a3466cc08ee7fb60a726ea1c4db6ecf48a9f847b9b7523bfb54b2ffaefee546
```

---

## TV-003 — Threshold mutation — single field change

Identical to TV-001 except threshold is 0.86 instead of 0.85. Hash MUST differ.

**Input (logical YAML, key order is irrelevant):**

```yaml
version: prml/0.1
claim_id: 01900000-0000-7000-8000-000000000000
created_at: '2026-05-01T12:00:00Z'
metric: accuracy
comparator: '>='
threshold: 0.86
dataset:
  id: imagenet-val-2012
  hash: e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
seed: 42
producer:
  id: studio-11.co
```

**Canonical bytes (UTF-8, exact):**

```yaml
claim_id: 01900000-0000-7000-8000-000000000000
comparator: '>='
created_at: '2026-05-01T12:00:00Z'
dataset:
  hash: e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
  id: imagenet-val-2012
metric: accuracy
producer:
  id: studio-11.co
seed: 42
threshold: 0.86
version: prml/0.1
```

**Expected hash (lowercase hex SHA-256 of canonical bytes):**

```
b96b5b8d613e29d8c28c1cf91c03821b02224c41188c6128743fa2d55639d4bb
```

---

## TV-004 — Optional fields — model and dataset.uri populated

Manifest with optional model.id, model.hash, and dataset.uri populated. Tests serialization of optional fields.

**Input (logical YAML, key order is irrelevant):**

```yaml
version: prml/0.1
claim_id: 01900000-0000-7000-8000-000000000001
created_at: '2026-06-15T09:30:00Z'
metric: f1
comparator: '>='
threshold: 0.78
dataset:
  id: glue-mrpc
  hash: 9b9a7c5e7d6c5f4e3d2c1b0a9f8e7d6c5b4a3928171615141312111009080706
  uri: https://gluebenchmark.com/tasks/mrpc
model:
  id: bert-base-uncased
  hash: 1f3c8a9d2b4e5c6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f
seed: 1337
producer:
  id: studio-11.co
```

**Canonical bytes (UTF-8, exact):**

```yaml
claim_id: 01900000-0000-7000-8000-000000000001
comparator: '>='
created_at: '2026-06-15T09:30:00Z'
dataset:
  hash: 9b9a7c5e7d6c5f4e3d2c1b0a9f8e7d6c5b4a3928171615141312111009080706
  id: glue-mrpc
  uri: https://gluebenchmark.com/tasks/mrpc
metric: f1
model:
  hash: 1f3c8a9d2b4e5c6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f
  id: bert-base-uncased
producer:
  id: studio-11.co
seed: 1337
threshold: 0.78
version: prml/0.1
```

**Expected hash (lowercase hex SHA-256 of canonical bytes):**

```
609308e259dc3e75909b6c81a6bf0230a34a0b9af6726e46675a66817a80d304
```

---

## TV-005 — Unicode in producer.id

Producer ID contains non-ASCII characters (Turkish). Tests UTF-8 byte-level handling.

**Input (logical YAML, key order is irrelevant):**

```yaml
version: prml/0.1
claim_id: 01900000-0000-7000-8000-000000000002
created_at: '2026-05-01T12:00:00Z'
metric: accuracy
comparator: '>='
threshold: 0.85
dataset:
  id: imagenet-val-2012
  hash: e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
seed: 42
producer:
  id: üniversite.edu.tr
```

**Canonical bytes (UTF-8, exact):**

```yaml
claim_id: 01900000-0000-7000-8000-000000000002
comparator: '>='
created_at: '2026-05-01T12:00:00Z'
dataset:
  hash: e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
  id: imagenet-val-2012
metric: accuracy
producer:
  id: üniversite.edu.tr
seed: 42
threshold: 0.85
version: prml/0.1
```

**Expected hash (lowercase hex SHA-256 of canonical bytes):**

```
6cf48a868f8f2fec59647d4b8327a27aba7dc219c14ab799ad85398a5aa9e1b6
```

---

## TV-006 — Maximum seed value

Seed = 2^64 - 1 = 18446744073709551615. Tests integer boundary handling.

**Input (logical YAML, key order is irrelevant):**

```yaml
version: prml/0.1
claim_id: 01900000-0000-7000-8000-000000000003
created_at: '2026-05-01T12:00:00Z'
metric: accuracy
comparator: '>='
threshold: 0.5
dataset:
  id: test-dataset
  hash: '0000000000000000000000000000000000000000000000000000000000000000'
seed: 18446744073709551615
producer:
  id: edge.example
```

**Canonical bytes (UTF-8, exact):**

```yaml
claim_id: 01900000-0000-7000-8000-000000000003
comparator: '>='
created_at: '2026-05-01T12:00:00Z'
dataset:
  hash: '0000000000000000000000000000000000000000000000000000000000000000'
  id: test-dataset
metric: accuracy
producer:
  id: edge.example
seed: 18446744073709551615
threshold: 0.5
version: prml/0.1
```

**Expected hash (lowercase hex SHA-256 of canonical bytes):**

```
57c71c567e0c4d86c691e311634730cd1ff0c65308f3a917d62d89d36d31c81d
```

---

## TV-007 — Minimum seed value

Seed = 0. Tests integer lower-boundary handling.

**Input (logical YAML, key order is irrelevant):**

```yaml
version: prml/0.1
claim_id: 01900000-0000-7000-8000-000000000004
created_at: '2026-05-01T12:00:00Z'
metric: accuracy
comparator: '>='
threshold: 0.5
dataset:
  id: test-dataset
  hash: '0000000000000000000000000000000000000000000000000000000000000000'
seed: 0
producer:
  id: edge.example
```

**Canonical bytes (UTF-8, exact):**

```yaml
claim_id: 01900000-0000-7000-8000-000000000004
comparator: '>='
created_at: '2026-05-01T12:00:00Z'
dataset:
  hash: '0000000000000000000000000000000000000000000000000000000000000000'
  id: test-dataset
metric: accuracy
producer:
  id: edge.example
seed: 0
threshold: 0.5
version: prml/0.1
```

**Expected hash (lowercase hex SHA-256 of canonical bytes):**

```
766d6ca6ee06b619bf4e49f586eff0e979adcd034abae31d2c52b93d00ef7b92
```

---

## TV-008 — Equality comparator

Comparator is `==` and threshold is an integer-valued float. Tests strict-match semantics.

**Input (logical YAML, key order is irrelevant):**

```yaml
version: prml/0.1
claim_id: 01900000-0000-7000-8000-000000000005
created_at: '2026-05-01T12:00:00Z'
metric: exact_match
comparator: ==
threshold: 1.0
dataset:
  id: synth-100
  hash: abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789
seed: 7
producer:
  id: studio-11.co
```

**Canonical bytes (UTF-8, exact):**

```yaml
claim_id: 01900000-0000-7000-8000-000000000005
comparator: ==
created_at: '2026-05-01T12:00:00Z'
dataset:
  hash: abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789
  id: synth-100
metric: exact_match
producer:
  id: studio-11.co
seed: 7
threshold: 1.0
version: prml/0.1
```

**Expected hash (lowercase hex SHA-256 of canonical bytes):**

```
fc2bf632dfb10bac8cf88b0c0756af2b53175c9b3078ae34aaf6ce63102c1b56
```

---

## TV-009 — Amendment manifest with prior_hash

Manifest amends TV-001 by raising threshold to 0.87. prior_hash points to TV-001's digest. Forms a 2-link chain.

**Input (logical YAML, key order is irrelevant):**

```yaml
version: prml/0.1
claim_id: 01900000-0000-7000-8000-000000000006
created_at: '2026-05-15T14:00:00Z'
metric: accuracy
comparator: '>='
threshold: 0.87
dataset:
  id: imagenet-val-2012
  hash: e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
seed: 42
producer:
  id: studio-11.co
prior_hash: 1a3466cc08ee7fb60a726ea1c4db6ecf48a9f847b9b7523bfb54b2ffaefee546
notes: Threshold raised after dataset re-curation found 12 mislabeled examples.
```

**Canonical bytes (UTF-8, exact):**

```yaml
claim_id: 01900000-0000-7000-8000-000000000006
comparator: '>='
created_at: '2026-05-15T14:00:00Z'
dataset:
  hash: e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
  id: imagenet-val-2012
metric: accuracy
notes: Threshold raised after dataset re-curation found 12 mislabeled examples.
prior_hash: 1a3466cc08ee7fb60a726ea1c4db6ecf48a9f847b9b7523bfb54b2ffaefee546
producer:
  id: studio-11.co
seed: 42
threshold: 0.87
version: prml/0.1
```

**Expected hash (lowercase hex SHA-256 of canonical bytes):**

```
29c60f7ccfb1f12777127785be25e3b2ca121b9b85b020f7bbd8e89a65ff1a04
```

---

## TV-010 — pass@k metric for code generation

Realistic LLM evaluation manifest using pass@k. Tests metric extensibility.

**Input (logical YAML, key order is irrelevant):**

```yaml
version: prml/0.1
claim_id: 01900000-0000-7000-8000-000000000007
created_at: '2026-07-01T08:00:00Z'
metric: pass@1
comparator: '>='
threshold: 0.65
dataset:
  id: humaneval
  hash: fedcba9876543210fedcba9876543210fedcba9876543210fedcba9876543210
  uri: https://github.com/openai/human-eval
model:
  id: claude-opus-4-7
  hash: 1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef
seed: 314159
producer:
  id: anthropic.com
```

**Canonical bytes (UTF-8, exact):**

```yaml
claim_id: 01900000-0000-7000-8000-000000000007
comparator: '>='
created_at: '2026-07-01T08:00:00Z'
dataset:
  hash: fedcba9876543210fedcba9876543210fedcba9876543210fedcba9876543210
  id: humaneval
  uri: https://github.com/openai/human-eval
metric: pass@1
model:
  hash: 1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef
  id: claude-opus-4-7
producer:
  id: anthropic.com
seed: 314159
threshold: 0.65
version: prml/0.1
```

**Expected hash (lowercase hex SHA-256 of canonical bytes):**

```
60f8eb35dd21c364811549b8a45ea50dc70a01ef7210cfcc43b6aa9915fc88c6
```

---

## TV-011 — AUROC with low threshold

Medical-imaging-style claim with threshold near 0.5 (random baseline). Tests low-threshold semantics.

**Input (logical YAML, key order is irrelevant):**

```yaml
version: prml/0.1
claim_id: 01900000-0000-7000-8000-000000000008
created_at: '2026-08-12T10:00:00Z'
metric: auroc
comparator: '>'
threshold: 0.55
dataset:
  id: chestx-ray-14
  hash: '1010101010101010101010101010101010101010101010101010101010101010'
seed: 2718
producer:
  id: research-hospital.example
```

**Canonical bytes (UTF-8, exact):**

```yaml
claim_id: 01900000-0000-7000-8000-000000000008
comparator: '>'
created_at: '2026-08-12T10:00:00Z'
dataset:
  hash: '1010101010101010101010101010101010101010101010101010101010101010'
  id: chestx-ray-14
metric: auroc
producer:
  id: research-hospital.example
seed: 2718
threshold: 0.55
version: prml/0.1
```

**Expected hash (lowercase hex SHA-256 of canonical bytes):**

```
91104f15ee95b7a61869e30bd1539abfd718652288daa6bb7418337a8ffc32de
```

---

## TV-012 — MAE for regression

Regression metric with `<=` comparator. Tests minimization-style claims.

**Input (logical YAML, key order is irrelevant):**

```yaml
version: prml/0.1
claim_id: 01900000-0000-7000-8000-000000000009
created_at: '2026-09-01T15:00:00Z'
metric: mae
comparator: <=
threshold: 2.5
dataset:
  id: boston-housing
  hash: 9999888877776666555544443333222211110000aaaaffffeeeeddddccccbbbb
seed: 1
producer:
  id: studio-11.co
```

**Canonical bytes (UTF-8, exact):**

```yaml
claim_id: 01900000-0000-7000-8000-000000000009
comparator: <=
created_at: '2026-09-01T15:00:00Z'
dataset:
  hash: 9999888877776666555544443333222211110000aaaaffffeeeeddddccccbbbb
  id: boston-housing
metric: mae
producer:
  id: studio-11.co
seed: 1
threshold: 2.5
version: prml/0.1
```

**Expected hash (lowercase hex SHA-256 of canonical bytes):**

```
ec1d18427451f0bd7886c6ac4027f07a779f899035c27ea52cb2765212866424
```

---

## TV-013 — Integer-valued threshold

Threshold supplied as a bare integer (90, not 90.0). PRML v0.1 §2 fixes threshold as float64, so it MUST canonicalize as `90.0`. Tests integer-to-float coercion in JSON parsers that distinguish int from float (Python, Rust).

**Input (logical YAML, key order is irrelevant):**

```yaml
version: prml/0.1
claim_id: 01900000-0000-7000-8000-00000000000a
created_at: '2026-06-01T12:00:00Z'
metric: accuracy_pct
comparator: '>='
threshold: 90
dataset:
  id: eval-2k
  hash: abcd1234abcd1234abcd1234abcd1234abcd1234abcd1234abcd1234abcd1234
seed: 42
producer:
  id: falsify.dev
```

**Canonical bytes (UTF-8, exact):**

```yaml
claim_id: 01900000-0000-7000-8000-00000000000a
comparator: '>='
created_at: '2026-06-01T12:00:00Z'
dataset:
  hash: abcd1234abcd1234abcd1234abcd1234abcd1234abcd1234abcd1234abcd1234
  id: eval-2k
metric: accuracy_pct
producer:
  id: falsify.dev
seed: 42
threshold: 90.0
version: prml/0.1
```

**Expected hash (lowercase hex SHA-256 of canonical bytes):**

```
cb9683ce70f5d45d407b827d0b9223d342ebd3600c560ec6a9e76dd336bf007d
```

---

## Invariants verified

- `TV-001.hash` == `TV-002.hash` (key-ordering invariance): `True`
- `TV-001.hash` != `TV-003.hash` (single-bit-of-content sensitivity): `True`
- `TV-009.prior_hash` == `TV-001.hash` (chain linkage works as specified)

---

## Implementer checklist

Run all 13 vectors through your canonicalizer + SHA-256. For each, assert:

```
assert sha256(canonicalize(input_spec)) == expected_hash
```

If any vector fails, do not ship the implementation. Open an issue at https://github.com/studio-11-co/falsify with the failing vector ID and the hash your implementation produces.

---

*Vectors generated by the falsify reference implementation v0.1.2. Regenerate with `python3 spec/test-vectors/v0.1/generate.py` after any change to `_canonicalize()`. Hash discrepancies between implementations are spec bugs, not implementation bugs — file accordingly.*
