# falsify-go — PRML v0.1 third reference implementation

A single-file Go implementation of PRML v0.1, demonstrating that the canonicalization is implementable in a *third* language byte-for-byte against the v0.1 conformance vectors.

**Status:** working draft, intended as portability evidence rather than a production tool. The Python reference implementation (`falsify`, in the repo root) remains the recommended runtime.

**Result:** 13 / 13 v0.1 conformance vectors pass byte-for-byte.

---

## Build & run

Requires Go ≥ 1.21. Standard library only — no external dependencies.

```bash
cd impl/go
go build -o falsify-go ./falsify.go

# Conformance suite
./falsify-go test-vectors ../../spec/test-vectors/v0.1/test-vectors.json

# Hash a manifest (JSON input)
./falsify-go hash my-manifest.json

# Verify a manifest against its sidecar; if --observed given, evaluate predicate
./falsify-go verify my-manifest.json --observed 0.876
```

Exit codes match the spec: `0` PASS, `2` BAD (bad input/spec), `3` TAMPERED, `10` FAIL, `11` GUARD (missing sidecar).

---

## What this is

About 450 lines of Go, zero runtime dependencies. The canonicalizer implements the §3.6 formal grammar: the plain-scalar predicate (`spec/grammar/README.md` §C5) and the float rule (§C4) are transcribed from the specification, not approximated from PyYAML — the 2026-09-13 audit found 21 inputs on which the earlier hand-rolled approximation was wrong. Verified on the 21 conformance vectors and the 92-vector edge suite., with the same plain-scalar predicate the JavaScript implementation uses (PyYAML rules, not Go's YAML library defaults).

Notably, Go's standard library handles two of the three portability findings **without workarounds** that the JavaScript implementation needed:

| Finding | JS workaround | Go behaviour |
|---|---|---|
| TV-006: uint64 max value (2⁶⁴-1 seed) | regex-based BigInt sentinel substitution | `json.Number` natively preserves the raw decimal string |
| TV-008: integer-valued float (`threshold: 1.0`) | field-level "always render as float" hint set | `json.Number` natively preserves the raw text including `.0` |
| TV-008: plain-scalar `==` quoting | hand-rolled predicate (same as JS) | hand-rolled predicate (same as JS) |

Reading: Go's `encoding/json` with `Decoder.UseNumber()` returns `json.Number` (a `string` type) for every numeric field, preserving the original textual form. The canonicalizer then emits that text directly, matching whatever PyYAML's `repr(float)` produced. JavaScript's `JSON.parse` collapses both into `Number` (binary64), losing both pieces of information.

This is a useful empirical finding: **Go stdlib has measurably better native support for the v0.1 canonicalization than JavaScript's stdlib does**. The v0.2 grammar work proposed in [`spec/v0.2/ROADMAP.md`](../../spec/v0.2/ROADMAP.md) eliminates this asymmetry by making `seed` a quoted string and forcing `threshold` to always emit with a decimal place — making language choice irrelevant to portability.

---

## What this is not

- Not a production tool. Use the Python reference implementation for running real evaluations.
- Not a complete YAML implementation. Loading `.yaml` files is not supported here; pass `.json` files (which the test vectors use).
- Not stable across spec versions. v0.2 will introduce a formal canonicalization grammar; this implementation will be rewritten to match.

---

## Why it exists

To prove the v0.1 specification is implementable from a third language without reading the Python or JavaScript reference. With three byte-for-byte conformant implementations across three languages, the spec is no longer "what PyYAML does" — it is "what the conformance suite says, reproducible across implementations."

The full portability analysis, covering all three implementations, is at [`spec/analysis/canonicalization-portability-v0.1.md`](../../spec/analysis/canonicalization-portability-v0.1.md).

---

## License

MIT. Same as the rest of the repository.
