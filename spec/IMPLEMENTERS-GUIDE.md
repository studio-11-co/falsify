# Implementing PRML from the specification

**For anyone writing a PRML canonicalizer or verifier in a language we have not.**
Published 2026-09-13. Canonical URL: https://spec.falsify.dev/IMPLEMENTERS-GUIDE.md

PRML has four reference implementations (Python, JavaScript, Go, Rust) and, as of
this date, **no implementation written by anyone other than the specification's
editor**. That is the largest open item in the specification's own status section:
four implementations by one author agreeing with each other is one opinion stated
four times, not evidence of interoperability. This page exists so that the first
independent implementation can be written from the text alone, checked against
the same corpus our CI uses, and listed.

Nothing here is a certification. There is no badge, no fee, no review board. There
is a corpus, a grammar, and a list.

## What you are implementing

A PRML manifest is a small YAML/JSON document (§2). An implementation does three
things with it:

1. **Canonicalize** — produce the exact byte sequence of §3 (key order, indentation,
   scalar spelling). This is where every past divergence lived.
2. **Hash** — SHA-256 of those bytes, lowercase hex (§4).
3. **Verify** — recompute the hash, compare to a published one, and if given an
   observed value, evaluate the comparator (§5) and exit with the code table of §7.

A verifier-only implementation (2 and 3, reading JSON) is a legitimate target and
is what the Go and Rust references are.

## Where the rules are

| Rule | Where it is stated | Notes |
|---|---|---|
| Field set, types, required fields | PRML-v0.1.md §2; `schema/prml-v0.1.schema.json`, `schema/prml-v0.2.schema.json` | `additionalProperties: false` — unknown keys are rejected |
| Canonical byte sequence | **`grammar/prml-canonical.abnf`** + **`grammar/README.md` C1–C7** (normative, §3.6) | The prose of §3 is secondary to these |
| Plain vs single-quoted strings | `grammar/README.md` **C5**, predicate P1–P6 with the YAML 1.1 resolver patterns verbatim | Transcribe the patterns. Do not approximate them. |
| Float spelling | `grammar/README.md` **C4** | Shortest round-trip digits; decimal for −4 ≤ e < 16, exponent form otherwise; `1.0e-05` not `1e-05` |
| `threshold` rendering | `grammar/README.md` **C6** | v0.1: always float. v0.2: by value — integral and below 2^53 → integer, otherwise float |
| What to reject | PRML-v0.1.md §3.2.1, §3.4, §3.5; `test-vectors/reject/README.md` | Duplicate keys, non-portable characters, non-NFC strings, non-finite thresholds |
| Exit codes | PRML-v0.1.md §7 | 0 pass · 10 fail · 3 tampered · 11 guard · 2 bad input |

The reference implementations are **conforming implementations of the grammar,
not its definition**. If your implementation and a reference disagree on an input
that no vector covers, the grammar decides; open an issue and we will add the
vector.

## The corpus you check against

All files live under `spec/test-vectors/` in the repository and are served from
`https://spec.falsify.dev/test-vectors/`.

| Suite | File | Count | What passing means |
|---|---|---|---|
| v0.1 normative | `v0.1/test-vectors.json` | 13 | your `canonical` bytes and `hash` equal the published ones, for every entry |
| v0.2 candidate | `v0.2/test-vectors.json` | 8 | same |
| §3.6 edge suite | `edge/edge-vectors.json` | 92 | same — these are the inputs at the edges of C4/C5/C6 on which three references were once wrong |
| reject suite | `reject/reject-vectors.json` + `reject/check_reject.py` | 20 | you refuse each one **for its stated reason** with exit code 2 (16 if you read JSON only; the four YAML-only cases are declared `SKIP`, not silently passed) |

Every positive vector has the same shape: `id`, `title`, `description`, `input`
(the manifest as a JSON object), `canonical` (the expected bytes), `hash`.

The from-grammar reference `grammar/check_grammar.py` reproduces all 113 positive
vectors without using any YAML library; reading it is a faster way into C4–C6 than
reading the references.

## How to run the check

Give your binary a `test-vectors <file>` command that prints one line per vector
and ends with `Result: N/N vectors passed.` — the same contract the four references
use — and a `hash <file>` (JSON, or YAML if you read it) that prints the hex digest.
Then:

```
your-impl test-vectors spec/test-vectors/v0.1/test-vectors.json
your-impl test-vectors spec/test-vectors/v0.2/test-vectors.json
your-impl test-vectors spec/test-vectors/edge/edge-vectors.json
python3 spec/test-vectors/reject/check_reject.py --reads json -- your-impl hash
```

(`--reads yaml,json` if you parse YAML; then `lock` or `hash` on the YAML files.)
`check_reject.py` scores a refusal only when your diagnostic names the vector's own
reason; a crash is not a refusal.

## What "conformant" means here

An implementation is **PRML 0.1 conformant** as a canonicalizer when it reproduces
all 13 + 8 + 92 positive vectors byte-for-byte with matching hashes and rejects the
reject suite as above. It is conformant as a verifier when, in addition, it
implements §5 (comparators, tolerance) and the §7 exit codes. We have no third
category and no partial credit; if a suite is not run, say which.

## The mistakes the first three implementations made

Read these before you write the string predicate. All were found on 2026-09-13 by
testing the grammar's edges; none was caught by the 21 conformance vectors.

- Treating `?` and `:` as unconditional first-character indicators. They force
  quoting only when the string is that single character or the next character is
  a space (`?x` is plain, `?` is quoted).
- Including `y`, `Y`, `n`, `N` in the boolean set. YAML 1.1's resolver does not;
  they are plain.
- Accepting an exponent without a decimal point as a float (`1e5`). The YAML 1.1
  float pattern requires the `.`; `1e5` is plain.
- Missing the sexagesimal and binary integer forms (`1:30`, `0b101`), underscores
  in digits (`1_000`), the merge and value tags (`<<`, `=`), and the lone `-` —
  all of which must be quoted.
- Letting the formatting library choose float notation. The rule is by exponent
  (C4); libraries switch at different magnitudes (`1e-05` came out as `0.00001`).
- Rendering v0.2 `threshold` by parsed type. Parsers disagree on whether `1300.0`
  is an integer; the rule is by value (C6).

Two limits worth knowing: the JavaScript `test-vectors` runner preserves big
integers with a text-unaware regex, so vector titles never spell 16+-digit numbers
(grammar README G6); and no schema-valid manifest can currently reach a nested key
named `threshold`, so the depth at which C6 applies is untested (G4).

## When it passes

Open an issue in `studio-11-co/falsify` titled `Independent implementation: <language>`
with a link to the repository and the four result lines above. Where we can build
it, we re-run the suites ourselves and list the implementation in the README under
"Independent implementations". Listing means the suites passed on the day we ran
them; it is not an endorsement, and we say so next to the name.

If something in the grammar or a vector turns out to be wrong, that is more valuable
than a passing run. Say so in the same place.
