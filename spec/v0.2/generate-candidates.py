"""
Generate v0.2 candidate test vectors (TV-013 to TV-018).

These vectors use the v0.1 grammar (PyYAML safe_dump canonicalization, same as
the existing 13 vectors) but exercise edge cases not covered in the normative
v0.1 suite. They are *candidates* for promotion to v0.2 normative status when
the spec freeze lands on 2026-05-22.

All three reference implementations (Python, Node.js, Go) MUST reproduce
these byte-for-byte. Any divergence is a new portability finding for v0.2.

Run:
  python3 spec/v0.2/generate-candidates.py

Outputs:
  spec/v0.2/test-vectors-candidates.json
  spec/v0.2/test-vectors-candidates.md
"""
import hashlib
import json
import yaml


def canonicalize(spec):
    """Match falsify._canonicalize exactly."""
    return yaml.safe_dump(
        spec,
        sort_keys=True,
        default_flow_style=False,
        allow_unicode=True,
        width=4096,
    )


def sha256(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


VECTORS = []

# TV-013: CJK Unicode in producer.id (extends TV-005's Latin-Extended)
VECTORS.append({
    "id": "TV-013",
    "title": "CJK Unicode in producer.id",
    "description": (
        "Producer ID contains CJK characters (Mandarin). Tests UTF-8 byte-level "
        "handling with multi-byte code points beyond Latin Extended. Distinct "
        "from TV-005 (Turkish) which uses Latin Extended-A only."
    ),
    "spec": {
        "version": "prml/0.1",
        "claim_id": "01900000-0000-7000-8000-00000000000a",
        "created_at": "2026-05-01T12:00:00Z",
        "metric": "accuracy",
        "comparator": ">=",
        "threshold": 0.9,
        "dataset": {
            "id": "test-dataset",
            "hash": "0000000000000000000000000000000000000000000000000000000000000000",
        },
        "seed": 42,
        "producer": {"id": "清华大学.cn"},
    },
})

# TV-014: Long notes field — multi-paragraph rationale (~600 chars)
VECTORS.append({
    "id": "TV-014",
    "title": "Long notes field with multiple paragraphs",
    "description": (
        "Notes field contains ~600 characters of multi-paragraph text. Tests "
        "that PyYAML safe_dump's line-width=4096 setting keeps the value on "
        "one line (no folding) and that escape sequences for newlines are "
        "rendered consistently across implementations."
    ),
    "spec": {
        "version": "prml/0.1",
        "claim_id": "01900000-0000-7000-8000-00000000000b",
        "created_at": "2026-05-01T12:00:00Z",
        "metric": "accuracy",
        "comparator": ">=",
        "threshold": 0.85,
        "dataset": {
            "id": "imagenet-val-2012",
            "hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        },
        "seed": 42,
        "producer": {"id": "studio-11.co"},
        "notes": (
            "Initial commit of the production accuracy claim for the v3 model release. "
            "Threshold of 0.85 was chosen based on the Q1 2026 incident review which "
            "established that the deployed system requires at least 85 percent top-1 "
            "accuracy on the ImageNet validation split to maintain user-facing service "
            "level objectives. The dataset hash pins the exact byte content of the "
            "validation split as distributed by the original ILSVRC organisers; any "
            "drift in those bytes will cause the verifier to refuse evaluation."
        ),
    },
})

# TV-015: All optional fields populated together
VECTORS.append({
    "id": "TV-015",
    "title": "All optional fields populated",
    "description": (
        "Manifest with dataset.uri, model.id, model.hash, model.uri, notes, "
        "and compute_envelope all populated. Tests the canonical ordering and "
        "rendering of every optional field defined in v0.1 simultaneously."
    ),
    "spec": {
        "version": "prml/0.1",
        "claim_id": "01900000-0000-7000-8000-00000000000c",
        "created_at": "2026-06-01T10:00:00Z",
        "metric": "f1",
        "comparator": ">=",
        "threshold": 0.82,
        "dataset": {
            "id": "glue-mrpc",
            "hash": "9b9a7c5e7d6c5f4e3d2c1b0a9f8e7d6c5b4a3928171615141312111009080706",
            "uri": "https://gluebenchmark.com/tasks/mrpc",
        },
        "model": {
            "id": "bert-base-uncased",
            "hash": "1f3c8a9d2b4e5c6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f",
            "uri": "https://huggingface.co/bert-base-uncased",
        },
        "seed": 1337,
        "producer": {"id": "studio-11.co"},
        "compute_envelope": "cpu-amd-epyc-7763, fp32, batch_size=32",
        "notes": "Reference benchmark, all optional fields populated for full provenance.",
    },
})

# TV-016: Chain length 3 — multiple amendments
# Generate hashes iteratively: TV-001 -> amend_1 -> amend_2
# We use TV-001's known hash as the prior_hash for the first amendment in this
# vector; the chain builds on top of TV-001 (already canonical and locked).
# The output of THIS vector is the SECOND amendment (link 3).
VECTORS.append({
    "id": "TV-016",
    "title": "Amendment chain length 3 (second amendment)",
    "description": (
        "Second amendment in a chain of three. The chain is "
        "TV-001 -> amendment_1 -> amendment_2 (this vector). The prior_hash "
        "field in this vector points to amendment_1 (the previous link), not "
        "back to TV-001. Tests that chains longer than 2 are constructible "
        "and that prior_hash is the immediate predecessor only."
    ),
    "_chain_construction": "Constructed below by computing amendment_1 first.",
    "spec": {
        "version": "prml/0.1",
        "claim_id": "01900000-0000-7000-8000-00000000000d",
        "created_at": "2026-08-01T16:00:00Z",
        "metric": "accuracy",
        "comparator": ">=",
        "threshold": 0.91,
        "dataset": {
            "id": "imagenet-val-2012",
            "hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        },
        "seed": 42,
        "producer": {"id": "studio-11.co"},
        "prior_hash": "AMENDMENT_1_HASH_PLACEHOLDER",
        "notes": "Second amendment: threshold raised again after Q3 audit.",
    },
})

# TV-017: Strict less-than comparator with regression
VECTORS.append({
    "id": "TV-017",
    "title": "Strict less-than comparator with regression metric",
    "description": (
        "Regression manifest using the strict-less-than comparator (<). Fills "
        "the comparator coverage gap in the v0.1 suite (TV-001 through TV-012 "
        "use >=, ==, >, <=; this exercises the remaining < operator)."
    ),
    "spec": {
        "version": "prml/0.1",
        "claim_id": "01900000-0000-7000-8000-00000000000e",
        "created_at": "2026-09-15T11:00:00Z",
        "metric": "rmse",
        "comparator": "<",
        "threshold": 1.5,
        "dataset": {
            "id": "ca-housing",
            "hash": "abababababababababababababababababababababababababababababababab",
        },
        "seed": 2024,
        "producer": {"id": "research-lab.example"},
    },
})

# TV-018: Very small float threshold (scientific-notation territory)
VECTORS.append({
    "id": "TV-018",
    "title": "Small-magnitude float threshold",
    "description": (
        "Threshold = 0.000001 (1e-6). Tests how PyYAML safe_dump renders "
        "small-magnitude floats (decimal vs scientific notation). Implementations "
        "that diverge here have a number-formatting issue and should re-implement "
        "Python's repr(float) shortest round-trip rule."
    ),
    "spec": {
        "version": "prml/0.1",
        "claim_id": "01900000-0000-7000-8000-00000000000f",
        "created_at": "2026-10-01T09:00:00Z",
        "metric": "false_positive_rate",
        "comparator": "<=",
        "threshold": 0.000001,
        "dataset": {
            "id": "fraud-detection-2026",
            "hash": "cdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcd",
        },
        "seed": 99,
        "producer": {"id": "fintech.example"},
    },
})


def to_repr(spec):
    """Pretty-print as readable YAML for the doc (NOT canonical)."""
    return yaml.safe_dump(spec, sort_keys=False, default_flow_style=False, allow_unicode=True)


# Compute canonical + hash for each vector. For TV-016 we need the chain.
# First: compute TV-001's hash (known) and an intermediate amendment_1.
TV001_HASH = "1a3466cc08ee7fb60a726ea1c4db6ecf48a9f847b9b7523bfb54b2ffaefee546"

# Synthesize amendment_1 (intermediate, not exported as a numbered TV)
amendment_1_spec = {
    "version": "prml/0.1",
    "claim_id": "01900000-0000-7000-8000-00000000000d",  # same claim_id as final TV-016
    "created_at": "2026-07-01T14:00:00Z",
    "metric": "accuracy",
    "comparator": ">=",
    "threshold": 0.88,
    "dataset": {
        "id": "imagenet-val-2012",
        "hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    },
    "seed": 42,
    "producer": {"id": "studio-11.co"},
    "prior_hash": TV001_HASH,
    "notes": "First amendment: threshold raised after dataset re-curation.",
}
amendment_1_canonical = canonicalize(amendment_1_spec)
amendment_1_hash = sha256(amendment_1_canonical)

# Patch TV-016's prior_hash to amendment_1_hash
for v in VECTORS:
    if v["id"] == "TV-016":
        v["spec"]["prior_hash"] = amendment_1_hash
        v["_amendment_1_canonical"] = amendment_1_canonical
        v["_amendment_1_hash"] = amendment_1_hash
        break

# Now compute canonical + hash for all 6 candidate vectors
hashes = {}
for v in VECTORS:
    canonical = canonicalize(v["spec"])
    h = sha256(canonical)
    v["canonical"] = canonical
    v["hash"] = h
    hashes[v["id"]] = h


# Write JSON
json_data = []
for v in VECTORS:
    entry = {
        "id": v["id"],
        "title": v["title"],
        "description": v["description"],
        "input": v["spec"],
        "canonical": v["canonical"],
        "hash": v["hash"],
    }
    if v["id"] == "TV-016":
        entry["intermediate_amendment_1"] = {
            "spec": amendment_1_spec,
            "canonical": v["_amendment_1_canonical"],
            "hash": v["_amendment_1_hash"],
            "note": "Intermediate amendment in the 3-link chain. TV-016's prior_hash points to this; this vector's prior_hash points to TV-001.",
        }
    json_data.append(entry)

with open("spec/v0.2/test-vectors-candidates.json", "w") as f:
    json.dump(json_data, f, indent=2, ensure_ascii=False)


# Write markdown
out = []
out.append("# PRML v0.2 Test Vector Candidates (TV-013 → TV-018)")
out.append("")
out.append("**Status:** working draft, not yet normative.")
out.append("**Target promotion:** v0.2 freeze on 2026-05-22.")
out.append("**Generator:** `spec/v0.2/generate-candidates.py`")
out.append("**License:** Community Specification License 1.0")
out.append("")
out.append("---")
out.append("")
out.append("## Purpose")
out.append("")
out.append("These six vectors exercise edge cases not covered in the normative v0.1 suite (TV-001 → TV-012). They are intended for promotion to the v0.2 normative suite, which the v0.2 ROADMAP commits to expanding to 24 vectors total.")
out.append("")
out.append("All six use the **v0.1 grammar** (the existing PyYAML `safe_dump` canonicalization), so they should pass against all three current reference implementations:")
out.append("")
out.append("- Python: `falsify.py` (uses PyYAML)")
out.append("- Node.js: `impl/js/falsify.js` (hand-rolled)")
out.append("- Go: `impl/go/falsify.go` (hand-rolled, stdlib only)")
out.append("")
out.append("Any divergence between implementations on these vectors is a new portability finding to be documented in `spec/analysis/canonicalization-portability-v0.1.md` and addressed in the v0.2 grammar.")
out.append("")
out.append("---")
out.append("")
out.append("## Index")
out.append("")
out.append("| ID | Title | Hash (first 12) |")
out.append("|---|---|---|")
for v in VECTORS:
    out.append(f"| `{v['id']}` | {v['title']} | `{v['hash'][:12]}` |")
out.append("")
out.append("---")
out.append("")

for v in VECTORS:
    out.append(f"## {v['id']} — {v['title']}")
    out.append("")
    out.append(v["description"])
    out.append("")
    out.append("**Input (logical YAML, key order is irrelevant):**")
    out.append("")
    out.append("```yaml")
    out.append(to_repr(v["spec"]).rstrip())
    out.append("```")
    out.append("")
    out.append("**Canonical bytes (UTF-8, exact):**")
    out.append("")
    out.append("```yaml")
    out.append(v["canonical"].rstrip())
    out.append("```")
    out.append("")
    out.append("**Expected hash (lowercase hex SHA-256 of canonical bytes):**")
    out.append("")
    out.append("```")
    out.append(v["hash"])
    out.append("```")
    out.append("")
    if v["id"] == "TV-016":
        out.append("**Intermediate amendment_1 in the chain (not a TV in itself):**")
        out.append("")
        out.append("```")
        out.append(f"hash: {amendment_1_hash}")
        out.append("```")
        out.append("")
        out.append("Chain order: `TV-001.hash` → `amendment_1.hash` → `TV-016.hash` (this vector).")
        out.append("")
    out.append("---")
    out.append("")

out.append("## Conformance check")
out.append("")
out.append("Run all three implementations against `test-vectors-candidates.json`:")
out.append("")
out.append("```bash")
out.append("# Python — use the existing _canonicalize directly")
out.append("python3 -c \"import json, hashlib, sys; sys.path.insert(0,'.'); import falsify; v=json.load(open('spec/v0.2/test-vectors-candidates.json')); [print(f'{x[\\\"id\\\"]}', 'PASS' if hashlib.sha256(falsify._canonicalize(x['input']).encode()).hexdigest()==x['hash'] else 'FAIL') for x in v]\"")
out.append("")
out.append("# Node.js")
out.append("node impl/js/falsify.js test-vectors spec/v0.2/test-vectors-candidates.json")
out.append("")
out.append("# Go")
out.append("./impl/go/falsify-go test-vectors spec/v0.2/test-vectors-candidates.json")
out.append("```")
out.append("")
out.append("Expected: 6/6 vectors pass in each implementation. Divergences are findings.")
out.append("")
out.append("---")
out.append("")
out.append("*Working draft, Community Specification License 1.0. Promotion to v0.2 normative on 2026-05-22.*")

text = "\n".join(out) + "\n"
with open("spec/v0.2/test-vectors-candidates.md", "w") as f:
    f.write(text)

print(f"Generated {len(VECTORS)} candidate vectors:")
for v in VECTORS:
    print(f"  {v['id']}: {v['hash'][:16]}...  {v['title']}")
print(f"\nIntermediate amendment_1 (for TV-016 chain):")
print(f"  hash: {amendment_1_hash[:16]}...")
print(f"\nWrote:")
print("  spec/v0.2/test-vectors-candidates.json")
print("  spec/v0.2/test-vectors-candidates.md")
