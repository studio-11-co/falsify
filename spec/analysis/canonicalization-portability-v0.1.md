# PRML v0.1 — Canonicalization Portability Findings

**Question:** Is the v0.1 canonicalization implementable in second and third languages byte-for-byte?

**Answer:** Yes — across **four** independent reference implementations (Python, Node.js, Go, Rust), all twelve v0.1 normative vectors and all six v0.2 candidate vectors reproduce byte-for-byte with matching SHA-256 digests. The exercise surfaced **three** non-obvious cross-language pitfalls in the v0.1 normative suite that the prose specification under-specifies. A subsequent run against six v0.2 candidate vectors (TV-013 → TV-018) surfaced a **fourth**, more subtle, finding around small-magnitude float rendering. The *severity* of each finding varies by language stdlib; with the 2026-05-01 patches in JS, Go, and Rust, all four implementations now agree on the canonical bytes for every vector. This document records all four findings so v0.2 can address each in formal grammar form.

**Sources:**

- Python reference: [`falsify.py`](../../falsify.py) — uses PyYAML `safe_dump`.
- Second implementation: [`impl/js/falsify.js`](../../impl/js/falsify.js) — Node.js, hand-rolled, zero runtime deps.
- Third implementation: [`impl/go/falsify.go`](../../impl/go/falsify.go) — Go, hand-rolled, stdlib plus `golang.org/x/text` (NFC check only).
- Fourth implementation: [`impl/rust/src/main.rs`](../../impl/rust/src/main.rs) — Rust, hand-rolled, three crate deps (`serde_json`, `sha2`, `unicode-normalization`).

**Result:** 12 / 12 v0.1 normative vectors pass byte-for-byte in **all four implementations**, and 6 / 6 v0.2 candidate vectors pass byte-for-byte in all four implementations after the Finding 4 patches.

---

## Why this matters

A specification that exists in only one implementation is indistinguishable from that implementation's bugs. v0.1 ships with twelve test vectors whose exact byte sequences are derived from PyYAML's `safe_dump`. Any second implementation that produces the same digest must produce the same canonical bytes. This is a strict constraint: a single byte difference anywhere in the output produces an entirely different SHA-256.

The Python reference implementation reaches canonical bytes by leaning on PyYAML's twenty-year-old `safe_dump` heuristics (sorted keys, plain-vs-quoted scalar decisions, float formatting). PyYAML is portable in the sense that the *parser* is portable, but the *emitter*'s output is a de-facto standard, not a de-jure one. This document is the audit of whether the emitter's behaviour is recoverable from the spec without reading PyYAML.

---

## Three findings

### Finding 1: 64-bit integer precision

**Vector affected:** TV-006 (`seed: 18446744073709551615`, the maximum unsigned 64-bit integer).

**Symptom:** A naïve JavaScript implementation that uses `JSON.parse` followed by `js-yaml`'s `dump` produces:

```
seed: 18446744073709552000
```

instead of the expected:

```
seed: 18446744073709551615
```

**Root cause:** ECMAScript's `Number` is IEEE-754 binary64. The largest safely representable integer is $2^{53}-1 \approx 9.007 \times 10^{15}$. The spec's allowed seed range is $[0, 2^{64}-1]$, which is roughly $1.8 \times 10^{19}$. Any seed above $2^{53}$ rounds during JSON parse, **before the canonicalizer ever runs**.

**Languages affected:**

| Language    | Native int range | TV-006 round-trips? |
|---          |---               |---                  |
| Python 3    | unbounded        | yes                 |
| JavaScript  | $2^{53}-1$       | **no** without BigInt |
| Go (`int64`) | $2^{63}-1$      | **no** for $> 2^{63}-1$ |
| Rust (`u64`) | $2^{64}-1$      | yes                 |
| Java (`long`) | $2^{63}-1$     | **no** for $> 2^{63}-1$ |

**Workaround in Node.js implementation:** Pre-process the JSON text with a regex that wraps any 16-or-more-digit integer in a sentinel string, parse, then unwrap to `BigInt`. This works but is a hack.

**v0.2 recommendation:** Either (a) restrict `seed` to $[0, 2^{53}-1]$ and lose nothing of practical value (no real ML benchmark uses seeds above $2^{53}$), or (b) require seed to be encoded as a quoted string in the canonical form, eliminating the parser-level precision concern entirely. Option (b) is cleaner and is the recommendation.

---

### Finding 2: Integer-valued floats lose their type

**Vector affected:** TV-008 (`threshold: 1.0`, an integer-valued float).

**Symptom:** A JS implementation that does `JSON.parse('{"threshold": 1.0}')` receives a `Number(1)`, indistinguishable at runtime from `Number(1)` produced by `JSON.parse('{"threshold": 1}')`. When that number is dumped via `js-yaml`, it emits `threshold: 1`, not `threshold: 1.0`. The Python reference, in contrast, preserves `float` vs `int` typing through PyYAML's load/dump cycle and emits `1.0`.

**Root cause:** Many languages' JSON parsers do not preserve the distinction between integer-valued floats and integers. JSON the format does not distinguish them either: `1.0` and `1` are both "numbers." The typing distinction lives in the producer's runtime, not in the wire format.

**Workaround in Node.js implementation:** A field-level hint: the canonicalizer maintains a small set, `FLOAT_FIELDS = {'threshold'}`, and forces any integer in those fields to render with a `.0` suffix. This works for v0.1 but is field-specific and not extensible.

**v0.2 recommendation:** Mark `threshold` (and any future float field) as **canonically rendered with at least one decimal place**, even when integer-valued. The canonical form for an integer-valued threshold is `1.0`, not `1`. This is a single sentence in the spec that closes the ambiguity.

---

### Finding 3: Plain-scalar quoting heuristics differ across YAML libraries

**Vector affected:** TV-008 (`comparator: ==`, unquoted plain scalar).

**Symptom:** `js-yaml` dumps the comparator string `==` as `comparator: '=='` (single-quoted). PyYAML emits the same value as `comparator: ==` (plain). For other comparators (`>=`, `<=`, `>`, `<`), both libraries quote: PyYAML because `>` is a YAML indicator character, `js-yaml` for the same reason.

**Root cause:** YAML 1.1/1.2 specifies a class of "plain scalars" that need not be quoted. The decision of *whether a particular string can be a plain scalar* is a complex predicate involving leading character (must not be a YAML indicator), middle content (no `: ` mapping ambiguity, no ` #` comment ambiguity), and resolution rules (must not look like a number, boolean, null, or timestamp). PyYAML and `js-yaml` implement this predicate with subtle differences. The `==` case is one of them: PyYAML accepts it as plain because no character in `==` is a YAML indicator and no resolution rule fires; `js-yaml` quotes defensively.

**Workaround in Node.js implementation:** Re-implement the plain-scalar predicate from scratch, matching PyYAML's behaviour. The implementation is in `needsQuoting(s)` and is approximately fifty lines of JavaScript. It checks: indicator-prefix, leading/trailing whitespace, colon-space and hash-space ambiguity, number-resolution regex, boolean/null set, timestamp regex, and control-character escape. With this hand-rolled predicate, TV-008 reproduces.

**v0.2 recommendation:** Adopt the path the v0.1 paper already names in §10 (limitations): publish a **formal canonicalization grammar in BNF or ABNF**. The grammar should include the plain-scalar predicate as a positive rule (`plain := first-char *plain-char ; first-char excludes [...]; plain-char excludes [...]`) rather than as a negative reference to a parent YAML spec. With a positive grammar, any second implementation can match without reverse-engineering an emitter's heuristics.

A simpler, more aggressive alternative: **always quote string scalars** in the canonical form. This eliminates the predicate entirely. Cost: ~10% larger canonical bytes for the typical PRML manifest. Benefit: zero ambiguity. We recommend this for v0.2 unless a strong reason emerges to keep the plain-scalar form.

---

### Finding 4: Float rendering for small-magnitude values diverges three ways

**Vector affected:** TV-018 (v0.2 candidate, `threshold: 0.000001` = 1e−6).

**Symptom:** A single floating-point input value of $10^{-6}$ canonicalises to **three distinct strings** across the three reference implementations, producing three different SHA-256 digests:

| Implementation | Canonical bytes for `threshold: 1e-6` |
|---|---|
| Python reference (PyYAML `safe_dump`) | `threshold: 1.0e-06`  |
| Node.js implementation | `threshold: 0.000001`  |
| Go implementation | `threshold: 1e-06`  |

**Root cause — three independent stdlib decisions:**

- **PyYAML** detects the float magnitude and emits scientific notation, with a quirky `.0` prefix on the mantissa (`1.0e-06`, not `1e-06`).
- **JavaScript** `Number.prototype.toString()` switches to scientific notation only below ~$10^{-7}$; for $10^{-6}$ it returns the decimal form `'0.000001'`.
- **Go** `json.Number` preserves the raw JSON text. The JSON encoding `1e-06` (which Go's `encoding/json` emits for very small floats) lacks PyYAML's mantissa-`.0` decoration.

Each is a defensible default in its language ecosystem. None of them agree.

**Languages affected:** essentially all of them, in different ways. Java's `Double.toString` differs from JavaScript. Rust's `f64::to_string` differs again. The float-to-string conversion is one of the most folkloric pieces of stdlib design across languages.

**Workaround in current implementations (added 2026-05-01 evening):** both JS and Go implementations now ship a small float-rendering helper (`pythonRepr` in JS, an updated `renderNumber` in Go) that detects scientific-notation float values and injects a `.0` mantissa to match PyYAML's output. With this patch, all three implementations pass TV-018 byte-for-byte. The patch is approximately 25 lines per language and is contained to the `threshold` field path.

The patch closes the immediate divergence but does **not** make the underlying issue go away — it makes JS and Go both reproduce PyYAML's specific float-formatting choice. Any fourth implementation (Rust, Java, Swift) faces the same predicament: either reverse-engineer Python's `repr(float)`, or wait for the v0.2 grammar fix below.

**Why this matters:** of the four findings, this is the most subtle. Findings 1, 2, and 3 surface as obviously wrong outputs (precision loss, missing `.0`, surprise quoting). Finding 4 surfaces as a **silently different valid float string** — every language has a defensible answer, but the conformance contract requires byte equality.

**v0.2 recommendation — strong:** adopt RFC-Q-04 from the v0.2 ROADMAP — **always quote numbers in the canonical form**. With `threshold: '0.000001'` (single-quoted decimal string) the language-stdlib float-formatting differences become invisible: every implementation reads the same string from the YAML and emits the same string back. The producer chooses the textual form once; verifiers honour it byte-for-byte.

**Alternative that does not work cleanly:** specifying a single numeric format in the spec ("scientific notation with mantissa `.0` for |x| < 1e-4") and forcing every implementation to reimplement Python's float repr to match. This is brittle, locale-sensitive, and punishes implementers; we do not recommend it.

**Status:** with the 2026-05-01 patch, TV-018 passes in all three reference implementations against the v0.1 grammar. It is now promotable to the v0.2 normative suite *as a v0.1-grammar test*. However, the strategic v0.2 fix (RFC-Q-04, always-quoted numbers) remains the right direction: under always-quoted numbers, the small-float patch becomes unnecessary, and a fourth implementation in any language can match the canonical form using only its native string handling — no `repr(float)` reverse engineering required.

---

## Severity asymmetry: language stdlib matters

The four findings are not equally severe across languages. The Go implementation surprisingly handled the first two with **no workaround** because Go's standard `encoding/json` package preserves the raw text of numeric fields when configured with `Decoder.UseNumber()`. The result is a `json.Number` typed `string`, which the canonicalizer can emit directly. Finding 4, by contrast, exposes a divergence that affects *every* language: each stdlib's float-to-string conversion is a defensible-but-unique opinion.

| Finding | Python (PyYAML) | JavaScript (stdlib `JSON`) | Go (stdlib `encoding/json`) | Rust (`serde_json`) |
|---|---|---|---|---|
| 1: uint64 max precision | OK (arbitrary-precision int) | **Workaround needed** (regex BigInt sentinel) | OK (`json.Number` raw string) | OK (`Number` preserves raw text) |
| 2: integer-valued float typing | OK (PyYAML preserves `float` type) | **Workaround needed** (field-level float hint set) | OK (`json.Number` preserves raw `.0`) | OK (`Number::to_string` preserves raw `.0`) |
| 3: plain-scalar `==` quoting | OK (PyYAML heuristic accepts) | **Hand-rolled predicate** | **Hand-rolled predicate** | **Hand-rolled predicate** |
| 4: small-float scientific-notation rendering | `1.0e-06` (PyYAML quirk) | `0.000001` → patched `1.0e-06` | `1e-06` → patched `1.0e-06` | `1e-6` → patched `1.0e-06` (all four now agree, post-patch) |

This is a useful empirical finding: **language choice affects how much extra work a second-implementation author has to do**. Go-from-scratch is closer to PyYAML's behaviour than JavaScript-from-scratch. A Rust implementation using `serde_json::value::Number` would likely fall in the same category as Go.

The lesson for v0.2: a formal grammar removes this asymmetry. With always-quoted strings and always-decimal floats, the language stdlib differences become invisible.

## Empirical conformance result

Three implementations now pass the v0.1 conformance suite:

**Node.js implementation** (`impl/js/falsify.js`, ~400 LOC):

```bash
$ node impl/js/falsify.js test-vectors spec/test-vectors/v0.1/test-vectors.json
PASS  TV-001 ... PASS  TV-012
Result: 12/12 vectors passed.
```

**Go implementation** (`impl/go/falsify.go`, ~450 LOC):

```bash
$ cd impl/go && go build -o falsify-go ./falsify.go
$ ./falsify-go test-vectors ../../spec/test-vectors/v0.1/test-vectors.json
PASS  TV-001 ... PASS  TV-012
Result: 12/12 vectors passed.
```

Both implementations use only their respective language's standard library. With three independent implementations across Python, JavaScript, and Go all reproducing the canonical bytes byte-for-byte, the v0.1 specification is no longer "what PyYAML does" — it is "what the conformance suite says, reproducibly."

The implementations are provided as evidence of portability, not as production tools. Production users should continue to use the Python reference implementation (`falsify`) at this stage. The Node.js and Go implementations will be promoted to first-class artifacts once v0.2 lands with the formal grammar that closes the three findings above.

---

## Action items for v0.2

1. **Restrict seed range or quote it.** Either cap at $[0, 2^{53}-1]$ or render as a quoted string. Recommendation: render as quoted string.
2. **Always render floats with at least one decimal place.** `threshold: 1.0`, never `threshold: 1`.
3. **Publish a formal canonicalization grammar.** Either an ABNF for a tight strict subset, or — preferred — a rule that all string scalars are always single-quoted in canonical form, eliminating the plain-scalar predicate.

These three actions together reduce the spec's portability surface from "depends on PyYAML's emitter heuristics" to "depends only on the formal grammar in §3." Any conformant second implementation can then be built from the specification text alone, without reading any reference implementation source.

---

## What this exercise does *not* prove

- It does not prove that **all** PyYAML edge cases are covered. The Node.js implementation matches the twelve current vectors, which exercise specific cases. Adding new vectors (Unicode normalisation, control characters, very long strings, line-folding edge cases) may reveal further divergences.
- It does not prove that **all language YAML libraries** agree with PyYAML. We tested Node.js + `js-yaml` (which diverged on `==`) and Go stdlib (which we hand-rolled rather than using `gopkg.in/yaml.v3`). Rust's `serde_yaml` and Java's SnakeYAML each have their own quirks. The findings above are likely a subset of the full surface.
- It does not prove that **future PyYAML versions** will preserve current behaviour. PyYAML's emitter is deliberately stable but not formally specified. A version bump could in principle change a quoting decision.

The right response to all three is the same: replace dependence on a reference *implementation* with dependence on a specification *grammar*. v0.2.

---

*Working draft v0.1, CC BY 4.0. Comments via [GitHub Discussions](https://github.com/studio-11-co/falsify/discussions/6) or `hello@falsify.dev`.*

---

## Control / format characters in string fields (measured 2026-06-17)

**Finding (reproduced in the Python reference).** A string field containing **U+0085 (NEL)**
does not round-trip through `yaml.safe_dump` → `yaml.safe_load`: `producer.id = "ab"`
canonicalizes and re-parses back to `"a b"`. The canonical bytes therefore do not represent
the input, so a lock/verify pair can disagree *within a single implementation*. Adjacent
characters behave inconsistently across the four impls: Python round-trips U+007F, U+FEFF and
U+2028 but the JS/Go/Rust control regex stops at U+007F and emits them raw or bare, yielding
different canonical bytes — and the JS U+2028 case produces non-round-trippable YAML. The
existing one-line "control characters untested" hedge (§ above) understated this: the documented
"always single-quote strings" recommendation would *not* fix the U+FEFF or U+2028 cases, because
the problem is round-trip fidelity / line-break interpretation, not quoting.

**Fix adopted (reference impl, additive — v0.1-safe).** `validate_manifest` now **rejects** any
manifest whose string fields contain a C0/C1 control character (incl. U+0085), U+007F, U+2028,
U+2029, or U+FEFF. These have no legitimate place in a PRML string field (metric, ids, etc.).
The rule is additive: no conformance vector contains such a character, so **no valid manifest's
hash changes and all 21 vectors still pass byte-identically**. Printable Unicode (emoji, CJK,
accents) is unaffected.

**v0.2 normative recommendation.** Promote this reject-on-input rule to the v0.2 grammar
(a closed character class for string scalars) rather than attempting to canonicalize the
un-canonicalizable. **Cross-impl follow-up:** the JS/Go/Rust reference implementations should
adopt the same reject rule on their next release; until then the Python reference is the one that
refuses to *mint* a non-portable manifest. Suggested conformance addition: a vector set asserting
each of U+0085 / U+007F / U+2028 / U+2029 / U+FEFF is rejected (a validation vector, not a hash vector).


---

**Postscript (2026-07).** Counts in this analysis reflect its writing date (12 v0.1 normative + 6 candidate vectors). The published suite grew to **13 v0.1 + 8 v0.2 = 21 positive vectors, plus 20 reject vectors**; all four implementations remain byte-for-byte in agreement across the full suite in CI.
