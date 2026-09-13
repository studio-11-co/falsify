# PRML v0.1 §3 — Formal grammar of the canonical serialization

**Published 2026-09-13. Normative** together with `prml-canonical.abnf`; referenced
from PRML-v0.1.md §3.6.

| File | What it is |
|---|---|
| `prml-canonical.abnf` | RFC 5234 ABNF recognising the canonical byte sequence of §3 |
| this README | the constraints C1–C7 that ABNF cannot express, and the record of how the grammar was verified |
| `check_grammar.py` | an emitter **and** a recogniser written from the grammar alone — no PyYAML, no reference canonicalizer — used to verify it |
| `candidate-vectors-2026-09-13.json` | 83 inputs built to exercise the edges of C4 and C5, with the canonical bytes and hash the grammar (and the reference canonicalizer) produce, and each reference implementation's agreement on that day |

## Why a grammar, and what changed

Until 2026-09-13, §3.5 said the reference canonicalizer was "normative for this
rendering". A specification that makes a program normative is documentation of
that program; an independent implementer had to reverse-engineer PyYAML's
`safe_dump` from prose and 21 vectors. This grammar replaces that: **the grammar
and C1–C7 are normative, and the reference canonicalizer is one conforming
implementation of them.**

Publishing the grammar **changes no canonical byte and no digest** of any valid
manifest. It describes what the reference canonicalizer already emits, and the
verification below is the proof.

## Verification (run `python3 check_grammar.py`)

1. **21 conformance vectors** (13 v0.1 + 8 v0.2): the from-grammar emitter
   reproduces the published `canonical` bytes and `hash` for every one, and the
   from-grammar recogniser accepts every one.
2. **14 deliberately malformed canonical texts** are rejected by the recogniser:
   CRLF, missing final LF, trailing space, three-space indent, root and nested
   key-order violations, root and nested duplicate keys, an integer `threshold`
   under v0.1, a non-canonical float spelling (`0.850`), a quoted scalar the
   predicate says should be plain, a plain scalar the predicate says should be
   quoted, a tab character.
3. **83 candidate vectors**: the from-grammar emitter reproduces the expected
   bytes for all 83.

The first run of the recogniser accepted one malformation (a duplicated root
key): an off-by-one in depth bookkeeping meant root-level duplicates and order
were never checked, and the "key order" negative had passed for the wrong reason
(a malformed mutation). Both were fixed before publication and the negative set
was widened. Recorded here because a recogniser whose negatives are not
exercised is a recogniser whose acceptance means nothing.

## Constraints the ABNF cannot express (normative)

**C1 — Depth.** A mapping at depth *d* renders each entry on a line beginning
with exactly 2·*d* spaces. The root mapping is depth 0.

**C2 — Order.** Entries of a mapping appear in ascending order of the key's
Unicode scalar values. For strings in the §3.4 portable set this equals
ascending byte order of the key's UTF-8 encoding. (§3.2.)

**C3 — Uniqueness.** No mapping contains the same key twice, at any depth.
(§3.2.1; a duplicate in the *input* is rejected with exit 2 before emission.)

**C4 — Float rendering.** The digits are the shortest decimal digit string that
parses back to the same IEEE 754 binary64 value ("shortest round-trip"). Write
the value as *d.ddd × 10^e* with 1 ≤ *d* < 10 (for zero, *e* = 0). Then:

- `float-decimal` when −4 ≤ *e* < 16 — e.g. `0.0001`, `0.85`, `90.0`,
  `1000000000000000.0`;
- `float-exp` when *e* < −4 or *e* ≥ 16 — e.g. `1.0e-05`, `1.5e-07`,
  `1.0e+16`, `5.0e-324`.

`float-exp` always has a `.` in the mantissa (`1.0e-05`, never `1e-05`), always
an explicit exponent sign, and at least two exponent digits. Non-finite values
have no production (§3.5). Negative zero renders `-0.0`.

**C5 — Plain-scalar predicate.** A string *s* (value or key) renders as
`plain-scalar` if and only if **all** of P1–P6 hold; otherwise as
`single-quoted`, with each `'` written twice.

- **P1** *s* is non-empty.
- **P2** *s*[0] is not one of `# , [ ] { } & * ! | > ' " % @ `` ` ``.
- **P3** it is not the case that *s*[0] ∈ {`?`, `:`, `-`} and (*s* has length 1
  or *s*[1] is a space).
- **P4** *s* neither begins nor ends with a space.
- **P5** for every position *i* > 0: not (*s*[i] = `:` and (*i* is the last
  position or *s*[i+1] is a space)); and not (*s*[i] = `#` and *s*[i−1] is a
  space).
- **P6** *s* matches none of the following patterns (YAML 1.1 implicit
  resolution; a plain scalar matching one would read back as a non-string):

```
bool       ^(?:yes|Yes|YES|no|No|NO|true|True|TRUE|false|False|FALSE|on|On|ON|off|Off|OFF)$
float      ^(?:[-+]?(?:[0-9][0-9_]*)\.[0-9_]*(?:[eE][-+][0-9]+)?
             |\.[0-9][0-9_]*(?:[eE][-+][0-9]+)?
             |[-+]?[0-9][0-9_]*(?::[0-5]?[0-9])+\.[0-9_]*
             |[-+]?\.(?:inf|Inf|INF)|\.(?:nan|NaN|NAN))$
int        ^(?:[-+]?0b[0-1_]+|[-+]?0[0-7_]+|[-+]?(?:0|[1-9][0-9_]*)
             |[-+]?0x[0-9a-fA-F_]+|[-+]?[1-9][0-9_]*(?::[0-5]?[0-9])+)$
null       ^(?:~|null|Null|NULL)$
timestamp  ^(?:[0-9]{4}-[0-9]{2}-[0-9]{2}
             |[0-9]{4}-[0-9]{1,2}-[0-9]{1,2}(?:[Tt]|[ \t]+)[0-9]{1,2}:[0-9]{2}:[0-9]{2}
              (?:\.[0-9]*)?(?:[ \t]*(?:Z|[-+][0-9]{1,2}(?::[0-9]{2})?))?)$
merge      ^<<$        value  ^=$        yaml  ^[!&*]$
```

Consequences worth spelling out, because three of the four reference
implementations got them wrong (see Divergences): `?x`, `:x`, `-x`, `y`, `n`,
`1e5`, `0o17`, `=x` are **plain**; `-`, `?`, `<<`, `=`, `1:30`, `1_000`, `0b101`,
`017`, `.5`, `5.`, `2026-05-01`, `yes`, `null`, `~` and the empty string are
**single-quoted**. Whitespace in P3–P5 means U+0020 only; every other character
PyYAML would treat as whitespace is outside the portable set and rejected first.

**C6 — Which production applies.** The manifest's *type* selects the production
— `null-literal` for null, `bool-literal` for booleans, `integer` for integers,
`float` for floats, `string` for strings — with one field rendered **by value**
rather than by type, at the root mapping only:

- under `prml/0.1`, `threshold` is a float64: an integer-valued threshold renders
  as `float` (`1` → `1.0`) (§3.5);
- under `prml/0.2`, `threshold` renders as `integer` if its value is an integer
  with magnitude below 2^53, and as `float` (C4) otherwise (RFC post-freeze
  clarification, 2026-09-13). `1300`, `1300.0` and `1.3e3` are one manifest;
  `9007199254740992` renders `9007199254740992.0`; `1e16` renders `1.0e+16`.

The rule is by value so that the bytes cannot depend on whether a producer typed
`1300` or `1300.0` — a distinction YAML, JSON and JavaScript's `Number` do not
reliably carry. *(Until 2026-09-13 this paragraph said v0.2 rendered by parsed
type; see Divergences, class D.)*

**C7 — Sequences (informative).** No v0.1 or v0.2 schema field is a sequence;
only free-form `metric_args` could contain one. The `sequence-N` productions
record what the reference emitter does (indentless `-` lines at the parent's
indentation; a mapping item puts its first entry on the `-` line). No
conformance vector exercises them and the cross-language CI does not test
them; they are informative until a vector does.

## Divergences found while writing this grammar (2026-09-13)

Stating C5 exactly made it possible to build inputs at its edges. An 83-input
battery (`candidate-vectors-2026-09-13.json`) — 62 strings placed in `notes`,
19 floats placed in `threshold`, two v0.2 integer-vs-float thresholds — was run
through all four reference implementations. **62 of 83 agree. On 21 they do
not.** None of the 21 is covered by a conformance vector, which is why the daily
CI has been green. Four classes:

| Class | Inputs | Who departs | Root cause |
|---|---|---|---|
| A — over-quoting | `?x` `:x` `y` `n` `Y` `N` `1e5` `1E5` `12e3` `1e-5` `0o17` | JS, Go, Rust | hand-rolled predicate treats `?`/`:` as unconditional indicators, includes single-letter bools, accepts an exponent without a `.`, and knows a `0o` octal that YAML 1.1 does not have |
| B — under-quoting | `-` `<<` `=` `1_000` `1:30` `190:20:30` `0b101` | JS, Go, Rust | predicate lacks the merge/value tags, sexagesimal and binary ints, underscore digits, and the lone-`-` block indicator |
| C — float notation | `threshold: 1e-05`, `-1e-05` | Rust only | renders `0.00001`: it reformats only when serde/ryu already chose exponent notation, so the *e* < −4 rule is never applied (ryu switches at 1e-6; Python at 1e-5) |
| D — v0.2 float-ness | `threshold: 1300.0` under `prml/0.2` | JavaScript only | `JSON.parse` yields the number 1300; the distinction the grammar (C6) makes cannot be observed |

**Status (updated later the same day).** Classes A, B and C were corrected on
2026-09-13: the JavaScript, Go and Rust predicates are now transcriptions of
§C5 (the resolver patterns verbatim), Rust's float rendering implements §C4
from the exponent, and the registry's `canonical.js` was corrected in step.
After correction: Python 83/83, Go 83/83, Rust 83/83, JavaScript 82/83 — and,
once class D was settled by the RFC clarification later the same day, 83/83 in
all four. The inputs were promoted to `spec/test-vectors/edge/` (92 vectors with
the ten boundary vectors for the new rule) and run in CI for all four. `candidate-vectors-2026-09-13.json` is kept as the dated
**pre-correction** snapshot; its `implementation_status_2026_09_13` field is
what was measured before the fix, not the current state.

Class D (`CV-V2b`) was not a bug in the same sense: JavaScript could not observe
the distinction the old C6 made, and the v0.2 RFC had never stated the rule the
vectors encoded. It was settled the same day, by value (RFC "Post-freeze
clarification", C6 above): Python, Go and Rust changed for `1300.0` inputs, no
published digest changed, and ten boundary vectors (EV-083..EV-092) were added
to the edge suite, which now has 92 vectors and passes in all four
implementations and the registry. `candidate-vectors-2026-09-13.json` keeps the
pre-decision measurement in `implementation_status_2026_09_13`; its expected
bytes for CV-V2b were updated to the decided rule (see its `note`).

## Gaps this grammar makes visible (for v0.3, not changed here)

- **G1** §3.4 does not name U+FFFE, U+FFFF and U+10FFFF. The reference emitter
  would double-quote a string containing them; the grammar has no double-quoted
  production, so such a string has no canonical form today. v0.3 should add them
  to the prohibited set (a MUST-reject, hence a reject vector, hence not an
  erratum-level change).
- **G2** Sequences are informative (C7) until a vector exercises them.
- **G3** The grammar bounds nothing about `metric_args` beyond C1–C6; a v0.3
  profile may wish to restrict its depth.
- **G4** The by-value/float-field rules of C6 are applied at the **root mapping
  only** by the Python reference and by `check_grammar.py`; JavaScript, Go and
  Rust apply the v0.1 float hint to any key named `threshold` at any depth. The
  two agree on every schema-valid manifest (nested `threshold` can only occur
  inside free-form `metric_args`), so no vector distinguishes them yet. A v0.3
  vector should.
- **G5** Go renders non-integral floats from the **raw JSON text** (with `.0`
  repairs) rather than from the value, on the assumption that the text is the
  shortest round-trip spelling. Every published vector is generated by Python's
  `repr`, so the assumption holds today; a JSON producer that writes `0.50` would
  not be canonicalized to `0.5` by Go. The v0.2 `threshold` path is by value.
- **G6** The JavaScript `test-vectors` runner (and the registry's
  `test-canonicalize.js`) preserve big integers with a text-unaware regex that
  wraps any 16+-digit run in value position — including one inside a `title`
  string, which turns the vector file into invalid JSON. Vector titles therefore
  spell large numbers as `2^53-1`, not as digits, until the runner parses
  strings properly. Found 2026-09-13 while adding EV-086..EV-089.

## Provenance

The plain-scalar predicate and the float rule were derived from the observable
behaviour of the reference canonicalizer (PyYAML 6.0.3 `safe_dump` with
`sort_keys=True, default_flow_style=False, width=inf, allow_unicode=True`),
transcribed, and then verified in the reverse direction by `check_grammar.py`,
which does not import PyYAML. Where PyYAML's behaviour and the prose of §3
disagreed, the prose was wrong in one place — §3.5 called the program
normative — and is corrected by §3.6.
