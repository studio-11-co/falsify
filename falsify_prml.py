#!/usr/bin/env python3
"""falsify — PRML v0.1 / v0.2 reference CLI (Python).

Commits an ML evaluation claim — metric, threshold, dataset hash, seed — to a
SHA-256 over the canonical manifest bytes *before* the run. Re-derivable by
anyone; edit the manifest after locking and the hash no longer matches.

Canonicalisation (PRML v0.1 §4): keys recursively sorted, block style, LF,
trailing whitespace stripped, exactly one trailing newline, UTF-8. This is the
same rule the Go / JS / Rust reference implementations use; all four produce
byte-identical canonical bytes on the 21 published conformance vectors.

Commands:
    falsify lock <spec.yaml|spec.json>            canonicalize, hash, write sidecar
    falsify verify <spec> [--observed <v>]        verify hash; if --observed, evaluate
    falsify hash <spec>                           print the canonical SHA-256 only
    falsify attest <spec>                         emit an in-toto (ITE-6) Statement
    falsify init <name>                           write a skeleton manifest
    falsify test-vectors <vectors.json>           run the conformance suite
    falsify --version

Exit codes: 0 PASS · 3 TAMPERED (hash mismatch) · 10 FAIL (threshold) ·
            2 bad input/spec · 11 guard (missing sidecar / lib).

Spec: https://spec.falsify.dev/v0.1
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys

__version__ = "0.3.9"

EXIT_PASS = 0
EXIT_BAD = 2
EXIT_TAMPERED = 3
EXIT_FAIL = 10
EXIT_GUARD = 11

REQUIRED_FIELDS = [
    "version", "claim_id", "created_at", "metric",
    "comparator", "threshold", "dataset", "seed", "producer",
]
REQUIRED_DATASET = ["id", "hash"]
REQUIRED_PRODUCER = ["id"]
VALID_COMPARATORS = {">=", "<=", ">", "<", "=="}
_HEX64 = re.compile(r"^[0-9a-f]{64}$")

# Characters that break canonical-byte portability across the reference impls:
# C0/C1 control chars (incl. U+0085 NEL, which PyYAML does not round-trip),
# U+007F DEL, the Unicode line/paragraph separators U+2028/U+2029, and U+FEFF
# (BOM / zero-width no-break space). These have no legitimate place in a PRML
# string field (metric, ids, etc.); a manifest containing them would canonicalize
# to different bytes — or fail to round-trip — across Python/JS/Go/Rust, so it is
# rejected at validation rather than silently producing a non-portable hash.
# Rejecting them is additive: no conformance vector contains these, so no valid
# manifest's hash changes. Printable Unicode (emoji, CJK, accents) is unaffected.
_FORBIDDEN_CHARS = re.compile(r"[\x00-\x1f\x7f-\x9f  ﻿]")


def _bad_char_fields(obj, path="") -> list[str]:
    """Return field paths whose string key or value contains a portability-breaking char."""
    out = []
    if isinstance(obj, str):
        if _FORBIDDEN_CHARS.search(obj):
            out.append(path or "(value)")
    elif isinstance(obj, dict):
        for k, v in obj.items():
            child = f"{path}.{k}" if path else str(k)
            # A forbidden char in a KEY canonicalizes non-portably just as in a
            # value, so keys are scanned too.
            if isinstance(k, str) and _FORBIDDEN_CHARS.search(k):
                out.append(f"{child} (key)")
            out.extend(_bad_char_fields(v, child))
    elif isinstance(obj, (list, tuple)):
        for i, v in enumerate(obj):
            out.extend(_bad_char_fields(v, f"{path}[{i}]"))
    return out


def _require_yaml():
    try:
        import yaml  # noqa: F401
        return yaml
    except ImportError:
        sys.stderr.write(
            "YAML support requires PyYAML: pip install pyyaml. "
            "Or pass a .json manifest.\n"
        )
        raise SystemExit(EXIT_GUARD)


# ─────────────────────────────────────────────────────────────────────────
# Canonicalisation — PRML v0.1 §4 (matches spec/test-vectors reference-target.py)
# ─────────────────────────────────────────────────────────────────────────

# PRML v0.1 §2 fixes `threshold` as float64: an integer-valued threshold MUST
# canonicalize as a float ("1.0"), matching the JS/Go/Rust reference impls.
# v0.2 relaxes threshold to int|float, so the coercion is v0.1-only.
_FLOAT_FIELDS_V01 = ("threshold",)


def canonicalize(manifest: dict) -> str:
    yaml = _require_yaml()
    m = dict(manifest)
    if m.get("version") == "prml/0.1":
        for field in _FLOAT_FIELDS_V01:
            v = m.get(field)
            if isinstance(v, int) and not isinstance(v, bool):
                m[field] = float(v)
    canonical = yaml.safe_dump(
        m,
        default_flow_style=False,
        sort_keys=True,
        width=float("inf"),
        allow_unicode=True,
    )
    return canonical.replace("\r\n", "\n").rstrip() + "\n"


def manifest_hash(manifest: dict) -> str:
    return hashlib.sha256(canonicalize(manifest).encode("utf-8")).hexdigest()


# ─────────────────────────────────────────────────────────────────────────
# Loading + validation
# ─────────────────────────────────────────────────────────────────────────

def load_manifest(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as fh:
        text = fh.read()
    if path.endswith(".json"):
        return json.loads(text)
    yaml = _require_yaml()
    return yaml.safe_load(text)


def validate_manifest(m: dict) -> list[str]:
    errors: list[str] = []
    if not isinstance(m, dict):
        return ["manifest must be a mapping"]
    for f in REQUIRED_FIELDS:
        if f not in m:
            errors.append(f"missing required field: {f}")
    if m.get("version") not in ("prml/0.1", "prml/0.2"):
        errors.append(f'version must be "prml/0.1" or "prml/0.2", got "{m.get("version")}"')
    if not isinstance(m.get("threshold"), (int, float)) or isinstance(m.get("threshold"), bool):
        errors.append("threshold must be a finite number")
    if m.get("comparator") and m["comparator"] not in VALID_COMPARATORS:
        errors.append("comparator must be one of " + ", ".join(sorted(VALID_COMPARATORS)))
    ds = m.get("dataset")
    if isinstance(ds, dict):
        for f in REQUIRED_DATASET:
            if f not in ds:
                errors.append(f"missing required field: dataset.{f}")
        if ds.get("hash") and not _HEX64.match(str(ds["hash"])):
            errors.append("dataset.hash must be 64 lowercase hex chars")
    prod = m.get("producer")
    if isinstance(prod, dict):
        for f in REQUIRED_PRODUCER:
            if f not in prod:
                errors.append(f"missing required field: producer.{f}")
    for fld in _bad_char_fields(m):
        errors.append(f"{fld}: contains a control / non-portable character "
                      f"(C0/C1, U+007F, U+2028/U+2029, or U+FEFF) — not allowed in a PRML string field")
    return errors


def evaluate_predicate(observed: float, comparator: str, threshold: float) -> bool:
    if comparator == ">=":
        return observed >= threshold
    if comparator == "<=":
        return observed <= threshold
    if comparator == ">":
        return observed > threshold
    if comparator == "<":
        return observed < threshold
    if comparator == "==":
        return observed == threshold
    raise ValueError(f"invalid comparator: {comparator}")


def to_intoto_statement(manifest: dict) -> dict:
    """Render a PRML manifest as an in-toto Attestation (ITE-6) Statement v1.

    This is the embed path for hosts that already speak in-toto / SLSA: a PRML
    lock becomes one more predicate type, no PRML CLI required. The Statement's
    `subject` is the locked claim (digest = the PRML manifest SHA-256) plus the
    dataset it is about; the `predicate` carries the pre-registered bar. Raises
    ValueError if the manifest is invalid (so you never attest a non-portable or
    malformed claim).

        from falsify_prml import to_intoto_statement
        stmt = to_intoto_statement(manifest)   # dict; json.dump it into your bundle
    """
    errors = validate_manifest(manifest)
    if errors:
        raise ValueError("invalid manifest: " + "; ".join(errors))
    h = manifest_hash(manifest)
    version = str(manifest["version"]).split("/", 1)[-1]  # "prml/0.1" -> "0.1"
    ds = manifest["dataset"]
    return {
        "_type": "https://in-toto.io/Statement/v1",
        "subject": [
            {"name": str(manifest["claim_id"]), "digest": {"sha256": h}},
            {"name": str(ds["id"]), "digest": {"sha256": str(ds["hash"])}},
        ],
        "predicateType": f"https://falsify.dev/prml/v{version}",
        "predicate": {
            "claim_id": manifest["claim_id"],
            "created_at": manifest["created_at"],
            "metric": manifest["metric"],
            "comparator": manifest["comparator"],
            "threshold": manifest["threshold"],
            "seed": manifest["seed"],
            "producer": manifest["producer"],
            "prml_version": manifest["version"],
            "manifest_sha256": h,
        },
    }


def _sidecar_path(spec_path: str) -> str:
    return re.sub(r"\.[^.]+$", "", spec_path) + ".prml.sha256"


# ─────────────────────────────────────────────────────────────────────────
# Commands
# ─────────────────────────────────────────────────────────────────────────

def cmd_lock(args) -> int:
    try:
        m = load_manifest(args.spec)
    except (OSError, ValueError) as e:
        sys.stderr.write(f"lock: cannot read {args.spec}: {e}\n")
        return EXIT_BAD
    errors = validate_manifest(m)
    if errors:
        sys.stderr.write("lock: invalid manifest:\n  - " + "\n  - ".join(errors) + "\n")
        return EXIT_BAD
    h = manifest_hash(m)
    sidecar = _sidecar_path(args.spec)
    with open(sidecar, "w", encoding="utf-8") as fh:
        fh.write(h + "\n")
    print(f"locked: {args.spec}")
    print(f"  canonical bytes: {len(canonicalize(m).encode('utf-8'))}")
    print(f"  sha256:          {h}")
    print(f"  sidecar:         {sidecar}")
    return EXIT_PASS


def cmd_hash(args) -> int:
    try:
        m = load_manifest(args.spec)
    except (OSError, ValueError) as e:
        sys.stderr.write(f"hash: cannot read {args.spec}: {e}\n")
        return EXIT_BAD
    # Validate before hashing: an invalid or non-portable manifest (e.g. one
    # carrying forbidden control characters) would otherwise yield a hash that
    # the other reference impls reject — a silent, non-portable commitment.
    # This matches `lock`/`verify` here and `hash` in the Go/Rust impls.
    errors = validate_manifest(m)
    if errors:
        sys.stderr.write("hash: invalid manifest:\n  - " + "\n  - ".join(errors) + "\n")
        return EXIT_BAD
    print(manifest_hash(m))
    return EXIT_PASS


def cmd_verify(args) -> int:
    try:
        m = load_manifest(args.spec)
    except (OSError, ValueError) as e:
        sys.stderr.write(f"verify: cannot read {args.spec}: {e}\n")
        return EXIT_BAD
    errors = validate_manifest(m)
    if errors:
        sys.stderr.write("verify: invalid manifest:\n  - " + "\n  - ".join(errors) + "\n")
        return EXIT_BAD

    recomputed = manifest_hash(m)
    expected = args.expected_hash
    if not expected:
        sidecar = _sidecar_path(args.spec)
        if not os.path.exists(sidecar):
            sys.stderr.write(
                f"verify: no --expected-hash and sidecar not found: {sidecar}\n"
                f"        run `falsify lock {args.spec}` first.\n"
            )
            return EXIT_GUARD
        with open(sidecar, "r", encoding="utf-8") as fh:
            expected = fh.read().strip()

    if recomputed != expected:
        print("TAMPERED")
        print(f"  recorded:    {expected}")
        print(f"  recomputed:  {recomputed}")
        return EXIT_TAMPERED

    if args.observed is None:
        print(f"OK  hash verified  sha256:{recomputed}")
        print("(no --observed value given; predicate not evaluated)")
        return EXIT_PASS

    try:
        observed = float(args.observed)
    except ValueError:
        sys.stderr.write("verify: --observed must be a finite number\n")
        return EXIT_BAD
    if evaluate_predicate(observed, m["comparator"], m["threshold"]):
        print(f"PASS  metric={m['metric']}  observed={observed}  {m['comparator']}  threshold={m['threshold']}")
        return EXIT_PASS
    print(f"FAIL  metric={m['metric']}  observed={observed}  NOT {m['comparator']}  threshold={m['threshold']}")
    return EXIT_FAIL


_SKELETON = """\
version: prml/0.1
claim_id: REPLACE_WITH_UUIDv7
created_at: "2026-01-01T00:00:00Z"
metric: accuracy
comparator: ">="
threshold: 0.90
dataset:
  id: your-dataset-id
  hash: REPLACE_WITH_64_LOWERCASE_HEX
seed: 42
producer:
  id: your-org-or-domain
"""


def cmd_init(args) -> int:
    out = args.name if args.name.endswith((".yaml", ".yml", ".json")) else args.name + ".prml.yaml"
    if os.path.exists(out):
        sys.stderr.write(f"init: {out} already exists\n")
        return EXIT_BAD
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(_SKELETON)
    print(f"wrote {out} — fill in the placeholders, then `falsify lock {out}`")
    return EXIT_PASS


def cmd_test_vectors(args) -> int:
    try:
        with open(args.vectors, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, ValueError) as e:
        sys.stderr.write(f"test-vectors: cannot read {args.vectors}: {e}\n")
        return EXIT_BAD
    if isinstance(data, list):
        vectors = data
    elif isinstance(data, dict):
        vectors = data.get("vectors", [])
    else:
        vectors = []
    passed = 0
    failed = 0
    for v in vectors:
        vid = v.get("id", "?")
        manifest = v.get("input") or v.get("manifest")
        exp_hash = v.get("hash")
        if manifest is None or exp_hash is None:
            continue
        got = manifest_hash(manifest)
        if got == exp_hash:
            passed += 1
        else:
            failed += 1
            print(f"  FAIL  {vid}  expected {exp_hash[:12]} got {got[:12]}")
    total = passed + failed
    print(f"{'PASS' if failed == 0 else 'FAIL'} — {passed}/{total} passed")
    return EXIT_PASS if failed == 0 else EXIT_FAIL


def cmd_attest(args) -> int:
    try:
        m = load_manifest(args.spec)
    except (OSError, ValueError) as e:
        sys.stderr.write(f"attest: cannot read {args.spec}: {e}\n")
        return EXIT_BAD
    try:
        stmt = to_intoto_statement(m)
    except ValueError as e:
        sys.stderr.write(f"attest: {e}\n")
        return EXIT_BAD
    print(json.dumps(stmt, indent=2, ensure_ascii=False, sort_keys=True))
    return EXIT_PASS


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="falsify", description="PRML reference CLI — pre-register ML eval claims.")
    p.add_argument("--version", action="version", version=f"falsify {__version__} (PRML v0.1/v0.2)")
    sub = p.add_subparsers(dest="cmd")

    sp = sub.add_parser("lock", help="canonicalize, hash, write sidecar")
    sp.add_argument("spec")
    sp.set_defaults(func=cmd_lock)

    sp = sub.add_parser("verify", help="verify hash; if --observed, evaluate the predicate")
    sp.add_argument("spec")
    sp.add_argument("--observed", default=None)
    sp.add_argument("--expected-hash", dest="expected_hash", default=None)
    sp.set_defaults(func=cmd_verify)

    sp = sub.add_parser("hash", help="print the canonical SHA-256 only")
    sp.add_argument("spec")
    sp.set_defaults(func=cmd_hash)

    sp = sub.add_parser("attest", help="emit an in-toto (ITE-6) Statement for the manifest")
    sp.add_argument("spec")
    sp.set_defaults(func=cmd_attest)

    sp = sub.add_parser("init", help="write a skeleton manifest")
    sp.add_argument("name")
    sp.set_defaults(func=cmd_init)

    sp = sub.add_parser("test-vectors", help="run the conformance suite against a vectors.json")
    sp.add_argument("vectors")
    sp.set_defaults(func=cmd_test_vectors)

    args = p.parse_args(argv)
    if not getattr(args, "func", None):
        p.print_help()
        return EXIT_BAD
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
