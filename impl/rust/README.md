# falsify-rs — PRML v0.1 fourth reference implementation

A Rust implementation of PRML v0.1 demonstrating that the canonicalization is implementable in a *fourth* language byte-for-byte against the v0.1 conformance vectors and the v0.2 candidate vectors.

**Status:** working draft, intended as portability evidence rather than a production tool. The Python reference implementation (`falsify`, in the repo root) remains the recommended runtime.

**Result:** 13 / 13 v0.1 vectors pass byte-for-byte. 8 / 8 v0.2 candidate vectors pass byte-for-byte (including TV-018, the small-magnitude-float case that surfaced Finding 4).

---

## Build & run

Requires Rust 1.70+.

```bash
cd impl/rust
cargo build --release

# Conformance suite
./target/release/falsify-rs test-vectors ../../spec/test-vectors/v0.1/test-vectors.json
./target/release/falsify-rs test-vectors ../../spec/v0.2/test-vectors-candidates.json

# Hash a manifest (JSON input)
./target/release/falsify-rs hash my-manifest.json

# Verify a manifest against its sidecar; if --observed given, evaluate predicate
./target/release/falsify-rs verify my-manifest.json --observed 0.876
```

Exit codes match the spec: `0` PASS, `2` BAD (bad input/spec), `3` TAMPERED, `10` FAIL, `11` GUARD (missing sidecar).

---

## What this is

About 650 lines of Rust, four runtime dependencies (`regex` for the §3.6 C5 resolver patterns, `serde_json` for JSON-with-preserved-number-text parsing, `sha2` for SHA-256 hashing). The canonicalizer implements the §3.6 formal grammar: the plain-scalar predicate (`spec/grammar/README.md` §C5) and the float rule (§C4) are transcribed from the specification, not approximated from PyYAML — the 2026-09-13 audit found 21 inputs on which the earlier hand-rolled approximation was wrong. Verified on the 21 conformance vectors and the 92-vector edge suite. We do not use any YAML library; all the work happens against the JSON source via serde_json.

Notable design points:

- **Plain-scalar predicate** — same rules as the JS and Go implementations: indicator-prefix, leading/trailing whitespace, colon-space and hash-space ambiguity, number-resolution regex, boolean/null set, timestamp regex, control-character escape. ~50 lines of hand-coded Rust.
- **Float rendering** (Finding 4 patch) — for the `threshold` field, scientific-notation values from serde_json are post-processed: mantissa receives a `.0` injection if missing, exponent receives 2-digit zero-padding and an explicit sign. About 15 lines of code.
- **Number preservation** — serde_json's `Number` preserves the source text when handed JSON that contains a number, so 64-bit precision is not lost. This is the same advantage Go's `json.Number` provides over JavaScript's `Number`.

---

## What this is not

- Not a production tool. Use the Python reference implementation for running real evaluations.
- Not a complete YAML implementation. Loading `.yaml` files is not supported here; pass `.json` files (which the test vectors use).
- Not stable across spec versions. v0.2 will introduce a formal canonicalization grammar; this implementation will be rewritten to match.

---

## Why it exists

To prove the v0.1 specification is implementable from a fourth language, in a different paradigm (Rust's strict ownership and trait system vs Python's dynamic typing, JavaScript's loose typing, Go's structural typing). With four byte-for-byte conformant implementations across four languages, the spec is robustly portable.

The full portability analysis covering all four implementations is at [`spec/analysis/canonicalization-portability-v0.1.md`](../../spec/analysis/canonicalization-portability-v0.1.md).

---

## License

MIT. Same as the rest of the repository.
