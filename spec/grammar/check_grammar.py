#!/usr/bin/env python3
"""check_grammar.py — an implementation of PRML §3 written FROM THE GRAMMAR.

Purpose. The reference canonicalizer (falsify_prml.py) reaches canonical bytes
through PyYAML's safe_dump. This file does NOT import PyYAML and does not
consult the reference canonicalizer. It implements the productions in
prml-canonical.abnf and the constraints C1–C7 in README.md, in two directions:

  emit(manifest)      dict -> canonical text        (the emitter side of §3)
  recognize(text)     canonical text -> parse or raise   (the ABNF recogniser)

and then checks itself against the published conformance corpus:

  * every conformance vector: emit(input) == canonical, sha256 == hash,
    and recognize(canonical) accepts;
  * a set of deliberately broken canonical texts that recognize() MUST reject
    (wrong indent, CRLF, key order, trailing space, missing final LF, an
    integer where §3.5 requires a float);
  * the divergence battery in candidate-vectors-2026-09-13.json, where
    emit() must reproduce the expected bytes for every case.

If all of that passes, the grammar is sufficient to write an implementation
that agrees with the reference on every published vector — which is the claim
§3.6 makes. Exit 0 on success, 1 on any failure. Run:  python3 check_grammar.py
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
import unicodedata
from decimal import Decimal
from pathlib import Path

HERE = Path(__file__).resolve().parent
SPEC = HERE.parent
VECTOR_FILES = [
    SPEC / "test-vectors" / "v0.1" / "test-vectors.json",
    SPEC / "test-vectors" / "v0.2" / "test-vectors.json",
]
CANDIDATES = HERE / "candidate-vectors-2026-09-13.json"

# ---------------------------------------------------------------------------
# C5 — plain-scalar predicate. Transcribed from the behaviour the grammar
# specifies (README §C5). The resolver patterns are the YAML 1.1 implicit
# resolvers; a plain string that would read back as any of these types must
# be single-quoted so that it reads back as a string.
# ---------------------------------------------------------------------------

_RESOLVERS = [re.compile(p, re.X) for p in (
    # bool
    r"^(?:yes|Yes|YES|no|No|NO|true|True|TRUE|false|False|FALSE|on|On|ON|off|Off|OFF)$",
    # float
    r"""^(?:[-+]?(?:[0-9][0-9_]*)\.[0-9_]*(?:[eE][-+][0-9]+)?
        |\.[0-9][0-9_]*(?:[eE][-+][0-9]+)?
        |[-+]?[0-9][0-9_]*(?::[0-5]?[0-9])+\.[0-9_]*
        |[-+]?\.(?:inf|Inf|INF)
        |\.(?:nan|NaN|NAN))$""",
    # int
    r"""^(?:[-+]?0b[0-1_]+
        |[-+]?0[0-7_]+
        |[-+]?(?:0|[1-9][0-9_]*)
        |[-+]?0x[0-9a-fA-F_]+
        |[-+]?[1-9][0-9_]*(?::[0-5]?[0-9])+)$""",
    # null  (the empty string is handled by P1)
    r"^(?:~|null|Null|NULL)$",
    # timestamp
    r"""^(?:[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]
        |[0-9][0-9][0-9][0-9]-[0-9][0-9]?-[0-9][0-9]?
         (?:[Tt]|[\ \t]+)[0-9][0-9]?
         :[0-9][0-9]:[0-9][0-9](?:\.[0-9]*)?
         (?:[\ \t]*(?:Z|[-+][0-9][0-9]?(?::[0-9][0-9])?))?)$""",
    # merge, value, yaml
    r"^(?:<<)$",
    r"^(?:=)$",
    r"^(?:!|&|\*)$",
)]

_P2_FIRST = set("#,[]{}&*!|>'\"%@`")


def is_plain(s: str) -> bool:
    """True iff the string renders as plain-scalar (README §C5, P1–P6)."""
    if s == "":                                           # P1
        return False
    if s[0] in _P2_FIRST:                                 # P2
        return False
    if s[0] in "?:-" and (len(s) == 1 or s[1] == " "):    # P3
        return False
    if s[0] == " " or s[-1] == " ":                       # P4
        return False
    for i in range(1, len(s)):                            # P5
        if s[i] == ":" and (i == len(s) - 1 or s[i + 1] == " "):
            return False
        if s[i] == "#" and s[i - 1] == " ":
            return False
    return not any(r.match(s) for r in _RESOLVERS)        # P6


def render_string(s: str) -> str:
    return s if is_plain(s) else "'" + s.replace("'", "''") + "'"


# ---------------------------------------------------------------------------
# C4 — float rendering, from the rule as stated (not from repr's own choice
# of notation). Shortest round-trip digits are the mathematically defined
# shortest digit string that parses back to the same binary64; Python's
# repr() is used only as the shortest-digits oracle.
# ---------------------------------------------------------------------------

def render_float(x: float) -> str:
    if x != x or x in (float("inf"), float("-inf")):
        raise ValueError("non-finite threshold is prohibited (§3.5)")
    d = Decimal(repr(x))
    sign = "-" if d.is_signed() else ""
    if d == 0:
        return sign + "0.0"
    digits = "".join(str(t) for t in d.as_tuple().digits).rstrip("0") or "0"
    e = d.adjusted()                     # value = d.ddd × 10^e, 1 <= d < 10
    if -4 <= e < 16:
        if e >= 0:
            intpart = digits[: e + 1].ljust(e + 1, "0")
            frac = digits[e + 1:] or "0"
        else:
            intpart = "0"
            frac = "0" * (-e - 1) + digits
        return f"{sign}{intpart}.{frac}"
    mant = digits[0] + "." + (digits[1:] or "0")
    return f"{sign}{mant}e{'+' if e >= 0 else '-'}{abs(e):02d}"


# ---------------------------------------------------------------------------
# C6 — which production applies. The manifest's type system decides:
#   None -> null-literal, bool -> bool-literal, int -> integer, float -> float,
#   str -> string. One field is version-aware (§3.5): under prml/0.1 an
#   integer-valued `threshold` is a float64 and MUST render as float.
# ---------------------------------------------------------------------------

FLOAT_FIELDS = {"prml/0.1": {"threshold"}}


def render_scalar(v, field: str, version: str) -> str:
    if v is None:
        return "null"
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, int):
        if field in FLOAT_FIELDS.get(version, set()):
            return render_float(float(v))
        return str(v)
    if isinstance(v, float):
        return render_float(v)
    if isinstance(v, str):
        return render_string(v)
    raise TypeError(f"unsupported scalar type {type(v).__name__}")


def emit(manifest: dict) -> str:
    """Canonical text for a manifest, per the grammar. Sequences follow the
    informative productions."""
    version = manifest.get("version", "")
    out: list[str] = []

    def walk(m: dict, depth: int) -> None:
        pad = "  " * depth
        keys = list(m.keys())
        if len(set(keys)) != len(keys):
            raise ValueError("duplicate key (C3)")
        for k in sorted(keys):                                 # C2
            v = m[k]
            if isinstance(v, dict):
                out.append(f"{pad}{render_string(k)}:")
                walk(v, depth + 1)
            elif isinstance(v, list):
                out.append(f"{pad}{render_string(k)}:")
                for item in v:
                    if isinstance(item, dict):
                        sub: list[str] = []
                        _walk_into(sub, item, depth + 1, k, version)
                        first = sub[0][len(pad) + 2:]
                        out.append(f"{pad}- {first}")
                        out.extend(sub[1:])
                    else:
                        out.append(f"{pad}- {render_scalar(item, k, version)}")
            else:
                out.append(f"{pad}{render_string(k)}: {render_scalar(v, k, version)}")

    def _walk_into(sub: list[str], m: dict, depth: int, field: str, ver: str) -> None:
        pad = "  " * depth
        for k in sorted(m.keys()):
            v = m[k]
            if isinstance(v, dict):
                sub.append(f"{pad}{render_string(k)}:")
                _walk_into(sub, v, depth + 1, k, ver)
            else:
                sub.append(f"{pad}{render_string(k)}: {render_scalar(v, k, ver)}")

    walk(manifest, 0)
    return "\n".join(out) + "\n"                               # §3.3


# ---------------------------------------------------------------------------
# Recogniser — checks a byte string against the ABNF shape and C1–C5.
# ---------------------------------------------------------------------------

_INT = re.compile(r"^-?(0|[1-9][0-9]*)$")
_FLOAT_DEC = re.compile(r"^-?(0|[1-9][0-9]*)\.[0-9]+$")
_FLOAT_EXP = re.compile(r"^-?[0-9]\.[0-9]+e[+-][0-9]{2,}$")
_SQ = re.compile(r"^'(?:[^']|'')*'$")
_PCHAR_BAD = re.compile("[\x00-\x1f\x7f-\x9f  ﻿￾￿\U0010ffff]")


class GrammarError(ValueError):
    pass


def _check_scalar(tok: str, field: str, version: str) -> str:
    """Return which production matched, or raise."""
    if tok in ("null", "true", "false"):
        return "literal"
    if _INT.match(tok):
        if field in FLOAT_FIELDS.get(version, set()):
            raise GrammarError(f"{field}: integer spelling where §3.5 requires float under {version}")
        return "integer"
    if _FLOAT_DEC.match(tok) or _FLOAT_EXP.match(tok):
        # C4: the spelling must be the one the rule produces for its own value
        if render_float(float(tok)) != tok:
            raise GrammarError(f"float {tok!r} is not the canonical rendering of its value")
        return "float"
    if _SQ.match(tok):
        inner = tok[1:-1].replace("''", "'")
        if _PCHAR_BAD.search(inner):
            raise GrammarError("non-portable character inside single-quoted scalar")
        if is_plain(inner):
            raise GrammarError(f"{tok} is single-quoted but the predicate says plain")
        return "single-quoted"
    if _PCHAR_BAD.search(tok):
        raise GrammarError("non-portable character in plain scalar")
    if not is_plain(tok):
        raise GrammarError(f"{tok!r} is plain but the predicate requires single quotes")
    return "plain"


def recognize(text: str) -> dict:
    if not text.endswith("\n"):
        raise GrammarError("canonical bytes must end with a single LF")
    if "\r" in text:
        raise GrammarError("CR is not permitted")
    lines = text.split("\n")[:-1]
    if not lines:
        raise GrammarError("empty document")
    version = ""
    for ln in lines:
        m = re.match(r"^version: (\S+)$", ln)
        if m:
            version = m.group(1)
    # C1 indentation and structure
    prev_depth = -1
    stack: list[set[str]] = []
    last_key: list[str | None] = []
    for ln in lines:
        if ln != ln.rstrip(" "):
            raise GrammarError(f"trailing whitespace: {ln!r}")
        stripped = ln.lstrip(" ")
        indent = len(ln) - len(stripped)
        if indent % 2:
            raise GrammarError(f"odd indentation: {ln!r}")
        depth = indent // 2
        if stripped.startswith("- "):
            # informative sequence item: accept scalar items only in the recogniser
            _check_scalar(stripped[2:], "", version)
            continue
        m = re.match(r"^(.+?):( (.*))?$", stripped)
        if not m:
            raise GrammarError(f"not an entry: {ln!r}")
        key_tok, has_value, val_tok = m.group(1), m.group(2) is not None, m.group(3)
        if key_tok.startswith("'"):
            # a quoted key may itself contain ':' — re-split on the closing quote
            mk = re.match(r"^('(?:[^']|'')*'):( (.*))?$", stripped)
            if not mk:
                raise GrammarError(f"bad quoted key: {ln!r}")
            key_tok, has_value, val_tok = mk.group(1), mk.group(2) is not None, mk.group(3)
        if _check_scalar(key_tok, "", version) not in ("plain", "single-quoted"):
            raise GrammarError(f"key must be a string: {key_tok!r}")
        key_text = key_tok[1:-1].replace("''", "'") if key_tok.startswith("'") else key_tok
        # depth bookkeeping
        if depth > prev_depth + 1:
            raise GrammarError(f"indentation jumps by more than one level: {ln!r}")
        while len(stack) > depth + 1:
            stack.pop(); last_key.pop()
        while len(stack) < depth + 1:
            stack.append(set()); last_key.append(None)
        if key_text in stack[depth]:
            raise GrammarError(f"duplicate key {key_text!r} (C3)")
        if last_key[depth] is not None and not (last_key[depth] < key_text):
            raise GrammarError(f"key order violation: {last_key[depth]!r} before {key_text!r} (C2)")
        stack[depth].add(key_text); last_key[depth] = key_text
        if has_value:
            if val_tok == "":
                raise GrammarError(f"empty value after ': ' : {ln!r}")
            _check_scalar(val_tok, key_text, version)
        prev_depth = depth
    return {"lines": len(lines), "version": version}


# ---------------------------------------------------------------------------
# Self-check
# ---------------------------------------------------------------------------

def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def main() -> int:
    ok = True
    # 1. conformance vectors
    total = 0
    for vf in VECTOR_FILES:
        vectors = json.loads(vf.read_text(encoding="utf-8"))
        for v in vectors:
            total += 1
            produced = emit(v["input"])
            good = produced == v["canonical"] and _sha(produced) == v["hash"]
            try:
                recognize(v["canonical"])
            except GrammarError as e:
                good = False
                print(f"  RECOGNISE-FAIL {v['id']}: {e}")
            if not good and produced != v["canonical"]:
                import difflib
                print(f"  EMIT-FAIL {v['id']} {v['title']}")
                for l in difflib.unified_diff(v["canonical"].splitlines(), produced.splitlines(), "expected", "grammar", lineterm=""):
                    print("    " + l)
            ok &= good
            print(f"  {'PASS' if good else 'FAIL'}  {v['id']:<7} {v['title']}")
    print(f"\nconformance: {total} vectors, {'all reproduced' if ok else 'FAILURES'}")

    # 2. negative self-tests: the recogniser must reject each mutation
    base = json.loads(VECTOR_FILES[0].read_text(encoding="utf-8"))[0]["canonical"]
    lines = base.rstrip("\n").split("\n")
    mutations = {
        "CRLF line endings": base.replace("\n", "\r\n"),
        "missing final LF": base.rstrip("\n"),
        "trailing space": base.replace("metric: accuracy\n", "metric: accuracy \n"),
        "three-space indent": base.replace("\n  hash:", "\n   hash:"),
        "key order swapped": "\n".join([lines[1], lines[0]] + lines[2:]) + "\n",
        "duplicate key": base.replace("seed: 42\n", "seed: 42\nseed: 42\n"),
        "int threshold under v0.1": base.replace("threshold: 0.85", "threshold: 1"),
        "non-canonical float spelling": base.replace("threshold: 0.85", "threshold: 0.850"),
        "quoted where plain required": base.replace("metric: accuracy", "metric: 'accuracy'"),
        "plain where quotes required": base.replace("comparator: '>='", "comparator: >="),
        "tab character": base.replace("metric: accuracy", "metric: acc\turacy"),
        "nested duplicate key": base.replace("  id: imagenet-val-2012\n", "  id: imagenet-val-2012\n  id: imagenet-val-2012\n"),
        "nested key order": base.replace("  hash: e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855\n  id: imagenet-val-2012\n",
                                         "  id: imagenet-val-2012\n  hash: e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855\n"),
        "root key order (version before threshold)": base.replace("threshold: 0.85\nversion: prml/0.1\n", "version: prml/0.1\nthreshold: 0.85\n"),
    }
    neg_ok = True
    for name, text in mutations.items():
        try:
            recognize(text)
            print(f"  NEG-FAIL  recogniser ACCEPTED: {name}")
            neg_ok = False
        except GrammarError:
            print(f"  NEG-PASS  rejected: {name}")
    ok &= neg_ok

    # 3. divergence battery (if present)
    if CANDIDATES.exists():
        cands = json.loads(CANDIDATES.read_text(encoding="utf-8"))
        bad = 0
        for c in cands:
            produced = emit(c["input"])
            if produced != c["canonical"] or _sha(produced) != c["hash"]:
                bad += 1
                print(f"  CAND-FAIL {c['id']} {c['title']}")
        print(f"candidates: {len(cands)} cases, {len(cands) - bad} reproduced by the grammar")
        ok &= bad == 0

    print("\nRESULT:", "OK" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
