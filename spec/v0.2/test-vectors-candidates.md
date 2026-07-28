# PRML v0.2 Test Vector Candidates (TV-013 → TV-018)

**Status:** HISTORICAL working draft, superseded by the 2026-05-22 freeze.
> **Post-freeze note (2026-07):** the numbers below reflect the pre-freeze state (12 v0.1 vectors, 6 candidates, a 24-vector target). The published outcome is: **13 v0.1 normative + 8 v0.2 vectors = 21 positive, plus 14 reject vectors**, all live at [spec.falsify.dev/v0.1](https://spec.falsify.dev/v0.1). This file is kept unchanged as a record of the RFC process.
**Target promotion:** v0.2 freeze on 2026-05-22.
**Generator:** `spec/v0.2/generate-candidates.py`
**License:** CC BY 4.0

---

## Purpose

These six vectors exercise edge cases not covered in the normative v0.1 suite (TV-001 → TV-012). They are intended for promotion to the v0.2 normative suite, which the v0.2 ROADMAP commits to expanding to 24 vectors total.

All six use the **v0.1 grammar** (the existing PyYAML `safe_dump` canonicalization), so they should pass against all three current reference implementations:

- Python: `falsify.py` (uses PyYAML)
- Node.js: `impl/js/falsify.js` (hand-rolled)
- Go: `impl/go/falsify.go` (hand-rolled, stdlib only)

Any divergence between implementations on these vectors is a new portability finding to be documented in `spec/analysis/canonicalization-portability-v0.1.md` and addressed in the v0.2 grammar.

---

## Index

| ID | Title | Hash (first 12) |
|---|---|---|
| `TV-013` | CJK Unicode in producer.id | `9e7096024ebb` |
| `TV-014` | Long notes field with multiple paragraphs | `e1c442fda6fc` |
| `TV-015` | All optional fields populated | `7d50bbac9c49` |
| `TV-016` | Amendment chain length 3 (second amendment) | `0f758e839683` |
| `TV-017` | Strict less-than comparator with regression metric | `3b7bbabc4392` |
| `TV-018` | Small-magnitude float threshold | `ff56657bd0d1` |

---

## TV-013 — CJK Unicode in producer.id

Producer ID contains CJK characters (Mandarin). Tests UTF-8 byte-level handling with multi-byte code points beyond Latin Extended. Distinct from TV-005 (Turkish) which uses Latin Extended-A only.

**Input (logical YAML, key order is irrelevant):**

```yaml
version: prml/0.1
claim_id: 01900000-0000-7000-8000-00000000000a
created_at: '2026-05-01T12:00:00Z'
metric: accuracy
comparator: '>='
threshold: 0.9
dataset:
  id: test-dataset
  hash: '0000000000000000000000000000000000000000000000000000000000000000'
seed: 42
producer:
  id: 清华大学.cn
```

**Canonical bytes (UTF-8, exact):**

```yaml
claim_id: 01900000-0000-7000-8000-00000000000a
comparator: '>='
created_at: '2026-05-01T12:00:00Z'
dataset:
  hash: '0000000000000000000000000000000000000000000000000000000000000000'
  id: test-dataset
metric: accuracy
producer:
  id: 清华大学.cn
seed: 42
threshold: 0.9
version: prml/0.1
```

**Expected hash (lowercase hex SHA-256 of canonical bytes):**

```
9e7096024ebbdea936ea4f92b35ce1fe1c2b5f1883d7196b6e10287aa620fa35
```

---

## TV-014 — Long notes field with multiple paragraphs

Notes field contains ~600 characters of multi-paragraph text. Tests that PyYAML safe_dump's line-width=4096 setting keeps the value on one line (no folding) and that escape sequences for newlines are rendered consistently across implementations.

**Input (logical YAML, key order is irrelevant):**

```yaml
version: prml/0.1
claim_id: 01900000-0000-7000-8000-00000000000b
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
notes: Initial commit of the production accuracy claim for the v3 model release. Threshold
  of 0.85 was chosen based on the Q1 2026 incident review which established that the
  deployed system requires at least 85 percent top-1 accuracy on the ImageNet validation
  split to maintain user-facing service level objectives. The dataset hash pins the
  exact byte content of the validation split as distributed by the original ILSVRC
  organisers; any drift in those bytes will cause the verifier to refuse evaluation.
```

**Canonical bytes (UTF-8, exact):**

```yaml
claim_id: 01900000-0000-7000-8000-00000000000b
comparator: '>='
created_at: '2026-05-01T12:00:00Z'
dataset:
  hash: e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
  id: imagenet-val-2012
metric: accuracy
notes: Initial commit of the production accuracy claim for the v3 model release. Threshold of 0.85 was chosen based on the Q1 2026 incident review which established that the deployed system requires at least 85 percent top-1 accuracy on the ImageNet validation split to maintain user-facing service level objectives. The dataset hash pins the exact byte content of the validation split as distributed by the original ILSVRC organisers; any drift in those bytes will cause the verifier to refuse evaluation.
producer:
  id: studio-11.co
seed: 42
threshold: 0.85
version: prml/0.1
```

**Expected hash (lowercase hex SHA-256 of canonical bytes):**

```
e1c442fda6fcc17881369da71b522f405a8679d887dbe88cdd495f45f5423b5e
```

---

## TV-015 — All optional fields populated

Manifest with dataset.uri, model.id, model.hash, model.uri, notes, and compute_envelope all populated. Tests the canonical ordering and rendering of every optional field defined in v0.1 simultaneously.

**Input (logical YAML, key order is irrelevant):**

```yaml
version: prml/0.1
claim_id: 01900000-0000-7000-8000-00000000000c
created_at: '2026-06-01T10:00:00Z'
metric: f1
comparator: '>='
threshold: 0.82
dataset:
  id: glue-mrpc
  hash: 9b9a7c5e7d6c5f4e3d2c1b0a9f8e7d6c5b4a3928171615141312111009080706
  uri: https://gluebenchmark.com/tasks/mrpc
model:
  id: bert-base-uncased
  hash: 1f3c8a9d2b4e5c6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f
  uri: https://huggingface.co/bert-base-uncased
seed: 1337
producer:
  id: studio-11.co
compute_envelope: cpu-amd-epyc-7763, fp32, batch_size=32
notes: Reference benchmark, all optional fields populated for full provenance.
```

**Canonical bytes (UTF-8, exact):**

```yaml
claim_id: 01900000-0000-7000-8000-00000000000c
comparator: '>='
compute_envelope: cpu-amd-epyc-7763, fp32, batch_size=32
created_at: '2026-06-01T10:00:00Z'
dataset:
  hash: 9b9a7c5e7d6c5f4e3d2c1b0a9f8e7d6c5b4a3928171615141312111009080706
  id: glue-mrpc
  uri: https://gluebenchmark.com/tasks/mrpc
metric: f1
model:
  hash: 1f3c8a9d2b4e5c6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f
  id: bert-base-uncased
  uri: https://huggingface.co/bert-base-uncased
notes: Reference benchmark, all optional fields populated for full provenance.
producer:
  id: studio-11.co
seed: 1337
threshold: 0.82
version: prml/0.1
```

**Expected hash (lowercase hex SHA-256 of canonical bytes):**

```
7d50bbac9c49306b5a8c5bd1ebb5052e30fcf16d52ec38470dfb8610c1c9d5e4
```

---

## TV-016 — Amendment chain length 3 (second amendment)

Second amendment in a chain of three. The chain is TV-001 -> amendment_1 -> amendment_2 (this vector). The prior_hash field in this vector points to amendment_1 (the previous link), not back to TV-001. Tests that chains longer than 2 are constructible and that prior_hash is the immediate predecessor only.

**Input (logical YAML, key order is irrelevant):**

```yaml
version: prml/0.1
claim_id: 01900000-0000-7000-8000-00000000000d
created_at: '2026-08-01T16:00:00Z'
metric: accuracy
comparator: '>='
threshold: 0.91
dataset:
  id: imagenet-val-2012
  hash: e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
seed: 42
producer:
  id: studio-11.co
prior_hash: 05bf194b8033140dba6970a623afbd5fa8f8634a6dd4c728000cb0f1f03ddf7d
notes: 'Second amendment: threshold raised again after Q3 audit.'
```

**Canonical bytes (UTF-8, exact):**

```yaml
claim_id: 01900000-0000-7000-8000-00000000000d
comparator: '>='
created_at: '2026-08-01T16:00:00Z'
dataset:
  hash: e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
  id: imagenet-val-2012
metric: accuracy
notes: 'Second amendment: threshold raised again after Q3 audit.'
prior_hash: 05bf194b8033140dba6970a623afbd5fa8f8634a6dd4c728000cb0f1f03ddf7d
producer:
  id: studio-11.co
seed: 42
threshold: 0.91
version: prml/0.1
```

**Expected hash (lowercase hex SHA-256 of canonical bytes):**

```
0f758e839683768fde1995463cd31c05c3e42343b8e289c57b5914154e6fe092
```

**Intermediate amendment_1 in the chain (not a TV in itself):**

```
hash: 05bf194b8033140dba6970a623afbd5fa8f8634a6dd4c728000cb0f1f03ddf7d
```

Chain order: `TV-001.hash` → `amendment_1.hash` → `TV-016.hash` (this vector).

---

## TV-017 — Strict less-than comparator with regression metric

Regression manifest using the strict-less-than comparator (<). Fills the comparator coverage gap in the v0.1 suite (TV-001 through TV-012 use >=, ==, >, <=; this exercises the remaining < operator).

**Input (logical YAML, key order is irrelevant):**

```yaml
version: prml/0.1
claim_id: 01900000-0000-7000-8000-00000000000e
created_at: '2026-09-15T11:00:00Z'
metric: rmse
comparator: <
threshold: 1.5
dataset:
  id: ca-housing
  hash: abababababababababababababababababababababababababababababababab
seed: 2024
producer:
  id: research-lab.example
```

**Canonical bytes (UTF-8, exact):**

```yaml
claim_id: 01900000-0000-7000-8000-00000000000e
comparator: <
created_at: '2026-09-15T11:00:00Z'
dataset:
  hash: abababababababababababababababababababababababababababababababab
  id: ca-housing
metric: rmse
producer:
  id: research-lab.example
seed: 2024
threshold: 1.5
version: prml/0.1
```

**Expected hash (lowercase hex SHA-256 of canonical bytes):**

```
3b7bbabc43922e97b9aa0c380bb6928ec37a0d5af486b92a6a9835b430a0ad11
```

---

## TV-018 — Small-magnitude float threshold

Threshold = 0.000001 (1e-6). Tests how PyYAML safe_dump renders small-magnitude floats (decimal vs scientific notation). Implementations that diverge here have a number-formatting issue and should re-implement Python's repr(float) shortest round-trip rule.

**Input (logical YAML, key order is irrelevant):**

```yaml
version: prml/0.1
claim_id: 01900000-0000-7000-8000-00000000000f
created_at: '2026-10-01T09:00:00Z'
metric: false_positive_rate
comparator: <=
threshold: 1.0e-06
dataset:
  id: fraud-detection-2026
  hash: cdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcd
seed: 99
producer:
  id: fintech.example
```

**Canonical bytes (UTF-8, exact):**

```yaml
claim_id: 01900000-0000-7000-8000-00000000000f
comparator: <=
created_at: '2026-10-01T09:00:00Z'
dataset:
  hash: cdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcd
  id: fraud-detection-2026
metric: false_positive_rate
producer:
  id: fintech.example
seed: 99
threshold: 1.0e-06
version: prml/0.1
```

**Expected hash (lowercase hex SHA-256 of canonical bytes):**

```
ff56657bd0d176dd8018c77461f38cdf5ec475b994a5061ef4d0f749bf4a7491
```

---

## Conformance check

Run all three implementations against `test-vectors-candidates.json`:

```bash
# Python — use the existing _canonicalize directly
python3 -c "import json, hashlib, sys; sys.path.insert(0,'.'); import falsify; v=json.load(open('spec/v0.2/test-vectors-candidates.json')); [print(f'{x[\"id\"]}', 'PASS' if hashlib.sha256(falsify._canonicalize(x['input']).encode()).hexdigest()==x['hash'] else 'FAIL') for x in v]"

# Node.js
node impl/js/falsify.js test-vectors spec/v0.2/test-vectors-candidates.json

# Go
./impl/go/falsify-go test-vectors spec/v0.2/test-vectors-candidates.json
```

Expected: 6/6 vectors pass in each implementation. Divergences are findings.

---

*Working draft, CC BY 4.0. Promotion to v0.2 normative on 2026-05-22.*
