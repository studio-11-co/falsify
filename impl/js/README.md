# falsify-js: PRML second reference implementation

A single-file Node.js implementation of PRML v0.1 and v0.2, demonstrating that the canonicalization is implementable in a second language byte-for-byte against the conformance vectors.

**Status:** working draft, intended as portability evidence rather than a production tool. The Python reference implementation (`falsify_prml.py`, in the repo root) remains the recommended runtime.

**Result:** 13 / 13 v0.1 vectors and 8 / 8 v0.2 vectors pass byte-for-byte; all 14 reject-vectors are correctly rejected.

---

## Run

No build step. Requires Node.js ≥ 18.

```bash
# Conformance suites
node falsify.js test-vectors ../../spec/test-vectors/v0.1/test-vectors.json
node falsify.js test-vectors ../../spec/test-vectors/v0.2/test-vectors.json

# Reject suite (run from the repo root)
python3 spec/test-vectors/reject/check_reject.py -- node impl/js/falsify.js lock

# Hash a manifest (JSON or YAML)
node falsify.js hash my-manifest.json

# Lock a manifest (writes <name>.prml.sha256 sidecar)
node falsify.js lock my-manifest.json

# Verify a manifest against its sidecar; if --observed given, evaluate predicate
node falsify.js verify my-manifest.json --observed 0.876
```

Exit codes match the spec: `0` PASS, `2` BAD (bad input/spec), `3` TAMPERED, `10` FAIL, `11` GUARD (missing sidecar).

---

## What this is

About 400 lines of Node.js, zero runtime dependencies beyond the Node.js standard library (`fs`, `path`, `crypto`). Optional dependency on `js-yaml` for loading `.yaml` files; not required for `.json` input.

The canonicalizer is hand-rolled to match PyYAML's `safe_dump` output exactly. It does not use a generic YAML serializer because `js-yaml` (and other YAML libraries) make different plain-scalar quoting decisions than PyYAML, producing canonical bytes that diverge from the v0.1 vectors.

Input handling is hardened against untrusted manifests:

- Parsed objects (JSON and YAML alike) are rejected if any key is `__proto__`, `constructor`, or `prototype`, at any nesting depth (prototype-pollution guard, with a bounded-depth DoS check).
- YAML input is parsed with `js-yaml`'s `CORE_SCHEMA`, so no custom or JS type tags (for example `!!js/function`) can be instantiated from manifest content.
- Strings containing control or non-portable characters (C0, DEL/C1, U+2028/U+2029, BOM) are rejected, mirroring the Python reference.

---

## What this is not

- Not a production tool. Use the Python reference implementation for running real evaluations.
- Not a complete YAML implementation. Loading `.yaml` files works only via `js-yaml`'s parser (CORE_SCHEMA); the canonicalizer is tuned to PRML manifest shapes, not arbitrary YAML.
- Not a browser library. This targets Node.js >= 18 (it uses `fs` and Node's `crypto`); the registry serves its own browser verifier.

---

## Why it exists

To prove the v0.1 specification is implementable from a second language without reading the Python reference. The exercise surfaced three non-obvious cross-language pitfalls — uint64 precision, integer-valued float typing, plain-scalar quoting heuristics — documented in [`spec/analysis/canonicalization-portability-v0.1.md`](../../spec/analysis/canonicalization-portability-v0.1.md). Those findings motivate the v0.2 formal grammar work.

---

## Dependency note

The optional `js-yaml` dependency is present only for parsing `.yaml` input files. If you pass `.json` files (which the test vectors do), no external dependencies are required.

```bash
# Optional, only for .yaml input loading
npm install js-yaml
```

---

## License

MIT. Same as the rest of the repository.
