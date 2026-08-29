"""Generate PRML v0.1 test vectors using the falsify reference canonicalization."""
import hashlib
import yaml
import json
from textwrap import indent

def canonicalize(spec):
    """Match falsify._canonicalize exactly.

    PRML v0.1 §2 fixes `threshold` as float64: an integer-valued threshold
    (e.g. 90) MUST canonicalize as a float ("90.0"), matching the
    Python/JS/Go/Rust reference impls. v0.2 relaxes threshold to int|float.
    """
    spec = dict(spec)
    if spec.get("version") == "prml/0.1":
        t = spec.get("threshold")
        if isinstance(t, int) and not isinstance(t, bool):
            spec["threshold"] = float(t)
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

# TV-001: Minimal valid manifest (Appendix A from spec)
VECTORS.append({
    "id": "TV-001",
    "title": "Minimal valid manifest",
    "description": "The smallest manifest that satisfies all required fields. Matches Appendix A of the PRML v0.1 specification.",
    "spec": {
        "version": "prml/0.1",
        "claim_id": "01900000-0000-7000-8000-000000000000",
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
    },
})

# TV-002: Key ordering — input keys in random order must produce same hash
VECTORS.append({
    "id": "TV-002",
    "title": "Key ordering — random insertion order",
    "description": "Same fields as TV-001 but constructed with reverse insertion order. Hash MUST equal TV-001 because canonicalization sorts keys lexicographically.",
    "spec": {
        "seed": 42,
        "producer": {"id": "studio-11.co"},
        "version": "prml/0.1",
        "threshold": 0.85,
        "metric": "accuracy",
        "dataset": {
            "hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            "id": "imagenet-val-2012",
        },
        "created_at": "2026-05-01T12:00:00Z",
        "comparator": ">=",
        "claim_id": "01900000-0000-7000-8000-000000000000",
    },
})

# TV-003: Different threshold — single-field change must change hash
VECTORS.append({
    "id": "TV-003",
    "title": "Threshold mutation — single field change",
    "description": "Identical to TV-001 except threshold is 0.86 instead of 0.85. Hash MUST differ.",
    "spec": {
        "version": "prml/0.1",
        "claim_id": "01900000-0000-7000-8000-000000000000",
        "created_at": "2026-05-01T12:00:00Z",
        "metric": "accuracy",
        "comparator": ">=",
        "threshold": 0.86,
        "dataset": {
            "id": "imagenet-val-2012",
            "hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        },
        "seed": 42,
        "producer": {"id": "studio-11.co"},
    },
})

# TV-004: F1 metric with optional model field
VECTORS.append({
    "id": "TV-004",
    "title": "Optional fields — model and dataset.uri populated",
    "description": "Manifest with optional model.id, model.hash, and dataset.uri populated. Tests serialization of optional fields.",
    "spec": {
        "version": "prml/0.1",
        "claim_id": "01900000-0000-7000-8000-000000000001",
        "created_at": "2026-06-15T09:30:00Z",
        "metric": "f1",
        "comparator": ">=",
        "threshold": 0.78,
        "dataset": {
            "id": "glue-mrpc",
            "hash": "9b9a7c5e7d6c5f4e3d2c1b0a9f8e7d6c5b4a3928171615141312111009080706",
            "uri": "https://gluebenchmark.com/tasks/mrpc",
        },
        "model": {
            "id": "bert-base-uncased",
            "hash": "1f3c8a9d2b4e5c6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f",
        },
        "seed": 1337,
        "producer": {"id": "studio-11.co"},
    },
})

# TV-005: Unicode in producer.id
VECTORS.append({
    "id": "TV-005",
    "title": "Unicode in producer.id",
    "description": "Producer ID contains non-ASCII characters (Turkish). Tests UTF-8 byte-level handling.",
    "spec": {
        "version": "prml/0.1",
        "claim_id": "01900000-0000-7000-8000-000000000002",
        "created_at": "2026-05-01T12:00:00Z",
        "metric": "accuracy",
        "comparator": ">=",
        "threshold": 0.85,
        "dataset": {
            "id": "imagenet-val-2012",
            "hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        },
        "seed": 42,
        "producer": {"id": "üniversite.edu.tr"},
    },
})

# TV-006: Maximum seed value (uint64 boundary)
VECTORS.append({
    "id": "TV-006",
    "title": "Maximum seed value",
    "description": "Seed = 2^64 - 1 = 18446744073709551615. Tests integer boundary handling.",
    "spec": {
        "version": "prml/0.1",
        "claim_id": "01900000-0000-7000-8000-000000000003",
        "created_at": "2026-05-01T12:00:00Z",
        "metric": "accuracy",
        "comparator": ">=",
        "threshold": 0.5,
        "dataset": {
            "id": "test-dataset",
            "hash": "0000000000000000000000000000000000000000000000000000000000000000",
        },
        "seed": 18446744073709551615,
        "producer": {"id": "edge.example"},
    },
})

# TV-007: Minimum seed value (zero)
VECTORS.append({
    "id": "TV-007",
    "title": "Minimum seed value",
    "description": "Seed = 0. Tests integer lower-boundary handling.",
    "spec": {
        "version": "prml/0.1",
        "claim_id": "01900000-0000-7000-8000-000000000004",
        "created_at": "2026-05-01T12:00:00Z",
        "metric": "accuracy",
        "comparator": ">=",
        "threshold": 0.5,
        "dataset": {
            "id": "test-dataset",
            "hash": "0000000000000000000000000000000000000000000000000000000000000000",
        },
        "seed": 0,
        "producer": {"id": "edge.example"},
    },
})

# TV-008: Strict-equality comparator
VECTORS.append({
    "id": "TV-008",
    "title": "Equality comparator",
    "description": "Comparator is `==` and threshold is an integer-valued float. Tests strict-match semantics.",
    "spec": {
        "version": "prml/0.1",
        "claim_id": "01900000-0000-7000-8000-000000000005",
        "created_at": "2026-05-01T12:00:00Z",
        "metric": "exact_match",
        "comparator": "==",
        "threshold": 1.0,
        "dataset": {
            "id": "synth-100",
            "hash": "abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789",
        },
        "seed": 7,
        "producer": {"id": "studio-11.co"},
    },
})

# TV-009: Amendment with prior_hash
VECTORS.append({
    "id": "TV-009",
    "title": "Amendment manifest with prior_hash",
    "description": "Manifest amends TV-001 by raising threshold to 0.87. prior_hash points to TV-001's digest. Forms a 2-link chain.",
    "spec": {
        "version": "prml/0.1",
        "claim_id": "01900000-0000-7000-8000-000000000006",
        "created_at": "2026-05-15T14:00:00Z",
        "metric": "accuracy",
        "comparator": ">=",
        "threshold": 0.87,
        "dataset": {
            "id": "imagenet-val-2012",
            "hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        },
        "seed": 42,
        "producer": {"id": "studio-11.co"},
        "prior_hash": "TV001_HASH_PLACEHOLDER",
        "notes": "Threshold raised after dataset re-curation found 12 mislabeled examples.",
    },
})

# TV-010: pass@k metric for code generation
VECTORS.append({
    "id": "TV-010",
    "title": "pass@k metric for code generation",
    "description": "Realistic LLM evaluation manifest using pass@k. Tests metric extensibility.",
    "spec": {
        "version": "prml/0.1",
        "claim_id": "01900000-0000-7000-8000-000000000007",
        "created_at": "2026-07-01T08:00:00Z",
        "metric": "pass@1",
        "comparator": ">=",
        "threshold": 0.65,
        "dataset": {
            "id": "humaneval",
            "hash": "fedcba9876543210fedcba9876543210fedcba9876543210fedcba9876543210",
            "uri": "https://github.com/openai/human-eval",
        },
        "model": {
            "id": "claude-opus-4-7",
            "hash": "1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
        },
        "seed": 314159,
        "producer": {"id": "anthropic.com"},
    },
})

# TV-011: AUROC with very small threshold
VECTORS.append({
    "id": "TV-011",
    "title": "AUROC with low threshold",
    "description": "Medical-imaging-style claim with threshold near 0.5 (random baseline). Tests low-threshold semantics.",
    "spec": {
        "version": "prml/0.1",
        "claim_id": "01900000-0000-7000-8000-000000000008",
        "created_at": "2026-08-12T10:00:00Z",
        "metric": "auroc",
        "comparator": ">",
        "threshold": 0.55,
        "dataset": {
            "id": "chestx-ray-14",
            "hash": "1010101010101010101010101010101010101010101010101010101010101010",
        },
        "seed": 2718,
        "producer": {"id": "research-hospital.example"},
    },
})

# TV-012: Empty optional notes field absent (not empty)
VECTORS.append({
    "id": "TV-012",
    "title": "MAE for regression",
    "description": "Regression metric with `<=` comparator. Tests minimization-style claims.",
    "spec": {
        "version": "prml/0.1",
        "claim_id": "01900000-0000-7000-8000-000000000009",
        "created_at": "2026-09-01T15:00:00Z",
        "metric": "mae",
        "comparator": "<=",
        "threshold": 2.5,
        "dataset": {
            "id": "boston-housing",
            "hash": "9999888877776666555544443333222211110000aaaaffffeeeeddddccccbbbb",
        },
        "seed": 1,
        "producer": {"id": "studio-11.co"},
    },
})

# TV-013: Integer-valued threshold must canonicalize as float64
VECTORS.append({
    "id": "TV-013",
    "title": "Integer-valued threshold",
    "description": "Threshold supplied as a bare integer (90, not 90.0). PRML v0.1 §2 fixes threshold as float64, so it MUST canonicalize as `90.0`. Tests integer-to-float coercion in JSON parsers that distinguish int from float (Python, Rust).",
    "spec": {
        "version": "prml/0.1",
        "claim_id": "01900000-0000-7000-8000-00000000000a",
        "created_at": "2026-06-01T12:00:00Z",
        "metric": "accuracy_pct",
        "comparator": ">=",
        "threshold": 90,
        "dataset": {
            "id": "eval-2k",
            "hash": "abcd1234abcd1234abcd1234abcd1234abcd1234abcd1234abcd1234abcd1234",
        },
        "seed": 42,
        "producer": {"id": "falsify.dev"},
    },
})


def to_repr(spec):
    """Pretty-print the input dict as readable YAML for the doc (NOT canonical)."""
    return yaml.safe_dump(spec, sort_keys=False, default_flow_style=False, allow_unicode=True)


# Compute canonical + hash for each, then patch TV-009 prior_hash
hashes = {}
for v in VECTORS:
    canonical = canonicalize(v["spec"])
    h = sha256(canonical)
    v["canonical"] = canonical
    v["hash"] = h
    hashes[v["id"]] = h

# Patch TV-009 prior_hash to point to TV-001
for v in VECTORS:
    if v["id"] == "TV-009":
        v["spec"]["prior_hash"] = hashes["TV-001"]
        canonical = canonicalize(v["spec"])
        v["canonical"] = canonical
        v["hash"] = sha256(canonical)

# Output: write a markdown file
out = []
out.append("# PRML v0.1 Test Vectors")
out.append("")
out.append("**Specification:** [PRML v0.1](https://spec.falsify.dev/v0.1)")
out.append("**Reference implementation:** [`falsify`](https://github.com/studio-11-co/falsify) — `_canonicalize()` in `falsify.py`")
out.append("**Generated:** 2026-05-01")
out.append("**Editor:** Cüneyt Öztürk — `hello@falsify.dev`")
out.append("**License:** Community Specification License 1.0")
out.append("")
out.append("---")
out.append("")
out.append("## Purpose")
out.append("")
out.append("These test vectors define the canonical-bytes-and-hash mapping for PRML v0.1 manifests. An implementation conforms to the specification if and only if, for each test vector, it produces:")
out.append("")
out.append("1. The exact canonical UTF-8 byte sequence shown under **Canonical bytes**, and")
out.append("2. The exact lowercase hex SHA-256 digest shown under **Expected hash**.")
out.append("")
out.append(f"Implementations in languages other than Python (Rust, Go, TypeScript, etc.) MUST reproduce all {len(VECTORS)} vectors. Discrepancies indicate either an implementation bug or a specification ambiguity that v0.2 must resolve.")
out.append("")
out.append("---")
out.append("")
out.append("## Index")
out.append("")
out.append("| ID | Title | Hash (first 12 chars) |")
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
    out.append("---")
    out.append("")

# Append note about TV-002 = TV-001 invariant
out.append("## Invariants verified")
out.append("")
out.append(f"- `TV-001.hash` == `TV-002.hash` (key-ordering invariance): `{hashes['TV-001'] == hashes['TV-002']}`")
out.append(f"- `TV-001.hash` != `TV-003.hash` (single-bit-of-content sensitivity): `{hashes['TV-001'] != hashes['TV-003']}`")
out.append("- `TV-009.prior_hash` == `TV-001.hash` (chain linkage works as specified)")
out.append("")
out.append("---")
out.append("")
out.append("## Implementer checklist")
out.append("")
out.append(f"Run all {len(VECTORS)} vectors through your canonicalizer + SHA-256. For each, assert:")
out.append("")
out.append("```")
out.append("assert sha256(canonicalize(input_spec)) == expected_hash")
out.append("```")
out.append("")
out.append("If any vector fails, do not ship the implementation. Open an issue at https://github.com/studio-11-co/falsify with the failing vector ID and the hash your implementation produces.")
out.append("")
out.append("---")
out.append("")
out.append("*Vectors generated by the falsify reference implementation v0.1.2. Regenerate with `python3 spec/test-vectors/v0.1/generate.py` after any change to `_canonicalize()`. Hash discrepancies between implementations are spec bugs, not implementation bugs — file accordingly.*")

text = "\n".join(out) + "\n"

with open("spec/test-vectors/v0.1/test-vectors.md", "w") as f:
    f.write(text)

# Also write a JSON file for programmatic consumption
json_data = []
for v in VECTORS:
    json_data.append({
        "id": v["id"],
        "title": v["title"],
        "description": v["description"],
        "input": v["spec"],
        "canonical": v["canonical"],
        "hash": v["hash"],
    })

with open("spec/test-vectors/v0.1/test-vectors.json", "w") as f:
    json.dump(json_data, f, indent=2, ensure_ascii=False)

print(f"Generated {len(VECTORS)} test vectors")
print(f"TV-001 hash: {hashes['TV-001']}")
print(f"TV-001 == TV-002 (key order invariance): {hashes['TV-001'] == hashes['TV-002']}")
print(f"TV-001 != TV-003 (content sensitivity): {hashes['TV-001'] != hashes['TV-003']}")
