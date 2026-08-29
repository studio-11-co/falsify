# PRML v0.1 conformance suite

Run any PRML implementation against the 13 canonical test vectors and report whether it produces byte-equivalent canonical bytes and matching SHA-256 hashes.

## Quick start

```bash
# Sanity-check the reference Python implementation
python3 conform.py "python3 reference-target.py"

# Test your implementation
python3 conform.py "/path/to/your/prml-binary"
python3 conform.py "node dist/cli.js conform"
python3 conform.py "go run ./cmd/falsify-conform"
python3 conform.py "cargo run --bin falsify-conform --release --quiet"
```

Expected output for a conforming implementation:

```
PRML v0.1 conformance — 13 vectors
target: python3 reference-target.py
file:   test-vectors.json

  PASS  TV-001  Minimal valid manifest
  PASS  TV-002  Key ordering — random insertion order
  ...
  PASS  TV-012  MAE for regression
  PASS  TV-013  Integer-valued threshold

PASS — 13/13 passed
```

Exit codes:

- `0` — all 13 vectors pass
- `1` — one or more failures (details printed)
- `2` — runner / IO error

## Protocol for the target binary

Your implementation must:

1. Read a single JSON object from **stdin** (the manifest fields)
2. Canonicalise it according to PRML v0.1 §4
3. Compute SHA-256 over the UTF-8 bytes of the canonical form
4. Write **a single JSON object** to stdout:

```json
{
  "canonical": "<canonical bytes as utf-8 string>",
  "hash": "<sha256 hex, no prefix>"
}
```

5. Exit with code `0` on success, non-zero on error

The runner times out at 10 seconds per vector. If your implementation needs longer than that to canonicalise a small YAML object, something is wrong.

### A reference target

[`reference-target.py`](reference-target.py) is a 40-line Python implementation that satisfies the protocol. Use it to sanity-check your runner setup, then swap in your own.

## What "byte-equivalent" means

The runner compares two things per vector:

1. **`canonical` strings** — character-by-character. Trailing newlines, line endings, key ordering, quoting — all must match.
2. **`hash` strings** — exact match (case-sensitive hex).

If `hash` matches but `canonical` differs, you have a bug that *happens* to round-trip to the same hash. That's worse than a hash mismatch — fix it.

If `canonical` matches but `hash` differs, your hashing function is broken (wrong algorithm, wrong encoding, wrong byte handling).

## Common failure modes

### Key ordering

PRML v0.1 §4 mandates lexicographic key ordering. Many languages' default YAML emitters preserve insertion order. Force sorted output:

- Python (PyYAML): `yaml.safe_dump(d, sort_keys=True)`
- JS (js-yaml): `yaml.dump(d, { sortKeys: true })`
- Go (gopkg.in/yaml.v3): wrap in `MarshalSorted` (custom)
- Rust (serde_yaml): use `serde_yaml::to_string` with a `BTreeMap`

### Unicode handling

The runner's `TV-005` includes a Unicode dataset hash field. Implementations must emit Unicode characters directly (not as `\xFC` escapes). For PyYAML: `allow_unicode=True`.

### Float formatting

`threshold: 0.85` and `threshold: 0.850` are different bytes. The reference impl uses Python's default float repr. JS / Go / Rust emit floats slightly differently — the test vectors include canonical float forms; match them.

### Trailing newline

The canonical form ends with exactly one `\n`. Two trailing newlines, no trailing newline, or `\r\n` will all fail.

## Adding new test vectors

We accept proposed new vectors via PR to this repo. Each vector must:

1. Have a `id` of the form `TV-NNN` (next available)
2. Include `title`, `description`, `input`, `canonical`, `hash`
3. Be reproducible: someone running the reference target on `input` must produce `canonical` and `hash` exactly

Do not modify existing vectors. The 13 v0.1 vectors are immutable; we use them to verify the spec hasn't drifted.

## Versioning

This suite covers PRML v0.1 only. v0.2 adds optional fields (streaming variant, runner attestation, revocation) — its conformance suite will be at `spec/test-vectors/v0.2/CONFORMANCE.md` once v0.2 freezes.

A v0.2-conforming impl MUST pass all v0.1 vectors. This is non-negotiable; v0.2 is fully backwards-compatible at the hash level for v0.1-shaped manifests. See [v0.2 RFC](https://spec.falsify.dev/v0.2-rfc) for details.

## License

This conformance harness is released under MIT (see repo root).
The vector data is published under the Community Specification License 1.0 alongside the spec (changed from CC BY 4.0 on 2026-08-29).
