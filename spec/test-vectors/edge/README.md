# Edge suite — §3.6 grammar edge cases (82 vectors)

**Added 2026-09-13.** Same file format as `../v0.1/test-vectors.json` (`id`,
`title`, `description`, `input`, `canonical`, `hash`); every reference
implementation runs it with its existing `test-vectors` command, and the
multi-language CI runs it for all four alongside the Appendix B suites.

## Why a separate suite

Appendix B (13 v0.1 + 8 v0.2 = **21 vectors**) is the normative conformance
suite of the specification and its count is quoted on every public surface.
This suite is different in origin: it was **derived from the formal grammar**
(§3.6, `spec/grammar/`), by building inputs at the edges of the plain-scalar
predicate (README §C5) and the float rule (§C4) — the kind of input the 21
vectors never contained and the kind on which three of the four reference
implementations turned out to be wrong. It is kept separate so that "21
conformance vectors" keeps meaning what it has always meant, and so that this
suite can grow as the grammar exposes more edges without renumbering Appendix B.

- 62 vectors place a string in `notes` (`?x`, `-`, `<<`, `1:30`, `1_000`, `y`,
  `1e5`, `0o17`, `2026-05-01`, `''`, …);
- 19 place a float in `threshold` under v0.1 (`1e-05`, `5e-324`, `1e16`, …);
- 1 places an integer `threshold` under v0.2 (`1300`).

Expected bytes and hashes are those of the reference canonicalizer and of the
from-grammar emitter `spec/grammar/check_grammar.py`, which agree on all 82.

## What is deliberately NOT here

`CV-V2b` from `spec/grammar/candidate-vectors-2026-09-13.json`: a v0.2 manifest
whose `threshold` is spelled `1300.0`. Python, Go and Rust render it `1300.0`
(parsed type); JavaScript and the registry render it `1300`, because neither
`JSON.parse` nor js-yaml can distinguish `1300.0` from `1300`. The v0.2 RFC does
not say which is right. Until it does, the case is recorded there with its
pre-correction status and is tested nowhere. Promoting it would encode a
specification decision inside a test file.

## History

The 83-input battery was first run on 2026-09-13 against all four
implementations: 62 agreed, 21 did not. JavaScript, Go and Rust were corrected
the same day (predicate transcribed from §C5; Rust's float rendering rewritten
to §C4; the registry's `canonical.js` corrected in step), after which 82/82
agree. The pre-correction measurement is preserved, per implementation, in the
candidate file's `implementation_status_2026_09_13` field.
