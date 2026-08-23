#!/usr/bin/env python3
"""falsify — PRML v0.1 / v0.2 reference CLI (Python).

Commits an ML evaluation claim — metric, threshold, dataset hash, seed — to a
SHA-256 over the canonical manifest bytes *before* the run. Re-derivable by
anyone; edit the manifest after locking and the hash no longer matches.

Canonicalisation (PRML v0.1 §4): keys recursively sorted, block style, LF,
trailing whitespace stripped, exactly one trailing newline, UTF-8. This is the
same rule the Go / JS / Rust reference implementations use; all four produce
byte-identical canonical bytes on the 21 published conformance vectors (which
feed pre-parsed objects). The YAML *parse* layer exists only in this Python
impl and impl/js (Go and Rust consume JSON vectors); the two are aligned to
YAML 1.2 core so the same manifest text hashes identically — see _core_loader
and tests/test_yaml_parse_parity.py.

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
import math
import os
import re
import sys
import unicodedata

__version__ = "0.3.13"

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

_CORE_LOADER = None


def _core_loader():
    # PyYAML's SafeLoader implements YAML 1.1, where unquoted yes/no/on/off/y/n
    # (any case) resolve to booleans. The JS reference and the registry parse
    # with js-yaml CORE_SCHEMA (YAML 1.2), where those tokens stay strings, so
    # the SAME manifest file could hash differently in Python vs JS. This loader
    # restricts the bool/null implicit resolvers to the YAML 1.2 core set so the
    # two YAML-parsing implementations agree byte-for-byte. (Go and Rust parse
    # only JSON test vectors, so they never see this layer.) Additive: no
    # conformance vector or valid manifest uses these tokens, so no existing
    # hash changes; see tests/test_yaml_parse_parity.py.
    global _CORE_LOADER
    if _CORE_LOADER is not None:
        return _CORE_LOADER
    yaml = _require_yaml()

    class _CoreSafeLoader(yaml.SafeLoader):
        def construct_mapping(self, node, deep=False):
            # A duplicate key is last-wins in every mainstream YAML loader, which
            # means the manifest a human reads and the manifest the hash binds can
            # differ with no error anywhere. That is a tamper channel inside a
            # tamper-evident format, so it is rejected rather than resolved.
            # RFC 7493 (I-JSON) §2.3 prohibits duplicate names for the same reason.
            seen = set()
            for key_node, _ in node.value:
                key = self.construct_object(key_node, deep=deep)
                try:
                    hashable = key in seen
                except TypeError:  # unhashable key — the base class will reject it
                    continue
                if hashable:
                    raise yaml.constructor.ConstructorError(
                        "while constructing a mapping", node.start_mark,
                        f"duplicate key {key!r} — a PRML manifest MUST NOT repeat a key",
                        key_node.start_mark,
                    )
                seen.add(key)
            return super().construct_mapping(node, deep=deep)

    # Rebuild implicit resolvers, dropping YAML-1.1-only bool/null spellings.
    _CoreSafeLoader.yaml_implicit_resolvers = {}
    for ch, mappings in yaml.SafeLoader.yaml_implicit_resolvers.items():
        kept = []
        for tag, regexp in mappings:
            if tag == "tag:yaml.org,2002:bool":
                # YAML 1.2 core: only true/false (any case). Drop yes/no/on/off/y/n.
                regexp = re.compile(r"^(?:true|True|TRUE|false|False|FALSE)$")
            elif tag == "tag:yaml.org,2002:null":
                # YAML 1.2 core: null/Null/NULL/~/empty. Drop the 1.1 extras.
                regexp = re.compile(r"^(?:~|null|Null|NULL|)$")
            kept.append((tag, regexp))
        _CoreSafeLoader.yaml_implicit_resolvers[ch] = kept
    _CORE_LOADER = _CoreSafeLoader
    return _CoreSafeLoader


def _no_duplicate_pairs(pairs):
    """json object_pairs_hook that rejects duplicate names, per RFC 7493 §2.3."""
    seen = set()
    for k, _ in pairs:
        if k in seen:
            raise ValueError(f"duplicate key {k!r} — a PRML manifest MUST NOT repeat a key")
        seen.add(k)
    return dict(pairs)


def _non_nfc_fields(obj, path="") -> list[str]:
    """Return field paths whose string key or value is not in Unicode NFC.

    "Öztürk" spelled NFD (macOS) and NFC (Linux) are the same text to a reader and
    different bytes to SHA-256, so the same claim would lock to two hashes depending
    on where it was authored. Non-NFC input is rejected rather than normalized:
    silently rewriting the text would change the bytes the author believes they
    locked, which is precisely what this format exists to prevent.
    """
    out = []
    if isinstance(obj, str):
        if not unicodedata.is_normalized("NFC", obj):
            out.append(path or "(value)")
    elif isinstance(obj, dict):
        for k, v in obj.items():
            child = f"{path}.{k}" if path else str(k)
            if isinstance(k, str) and not unicodedata.is_normalized("NFC", k):
                out.append(f"{child} (key)")
            out.extend(_non_nfc_fields(v, child))
    elif isinstance(obj, (list, tuple)):
        for i, v in enumerate(obj):
            out.extend(_non_nfc_fields(v, f"{path}[{i}]"))
    return out


def load_manifest(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as fh:
        text = fh.read()
    if path.endswith(".json"):
        return json.loads(text, object_pairs_hook=_no_duplicate_pairs)
    yaml = _require_yaml()
    # nosec B506 — _core_loader() returns a yaml.SafeLoader subclass (only its
    # bool/null implicit resolvers are narrowed to YAML 1.2 core); it cannot
    # instantiate arbitrary objects, so this is a safe load.
    try:
        return yaml.load(text, Loader=_core_loader())  # nosec B506
    except yaml.YAMLError as e:
        # Callers handle ValueError; a YAML parse failure is a malformed manifest,
        # not a crash, and must read as one (duplicate keys arrive through here).
        raise ValueError(str(e).replace("\n", " ").strip()) from e


def validate_manifest(m: dict) -> list[str]:
    errors: list[str] = []
    if not isinstance(m, dict):
        return ["manifest must be a mapping"]
    for f in REQUIRED_FIELDS:
        if f not in m:
            errors.append(f"missing required field: {f}")
    if m.get("version") not in ("prml/0.1", "prml/0.2"):
        errors.append(f'version must be "prml/0.1" or "prml/0.2", got "{m.get("version")}"')
    thr = m.get("threshold")
    if not isinstance(thr, (int, float)) or isinstance(thr, bool):
        errors.append("threshold must be a finite number")
    elif not math.isfinite(thr):
        # An infinite or NaN threshold locks and verifies cleanly while asserting
        # nothing: `<= .inf` passes for every observation, and any comparison
        # against .nan fails for every observation. Either way the manifest carries
        # a bar that no result can inform, which defeats the point of locking one.
        errors.append(
            "threshold must be a finite number: "
            f"{thr} states a bar that no observation can fail or meet"
        )
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
    for fld in _non_nfc_fields(m):
        errors.append(f"{fld}: string is not in Unicode NFC — the same text in a "
                      f"different normalization form hashes differently; normalize to NFC")
    errors.extend(_schema_conformance_errors(m))
    return errors


# Full published-schema conformance (spec/schema/prml-v0.1.schema.json).
# Added in v0.3.12 after Andes' independent interoperability assessment
# (finding 1): the reference validator accepted manifests the published
# JSON Schema rejects (UUIDv4 claim_ids, unknown fields, over-long values).
# The validators and the schema must agree, or "validated PRML" means two
# different things depending on which artifact a verifier picked up.
_UUIDV7 = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-7[0-9a-fA-F]{3}-[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}$")
_RFC3339 = re.compile(r"^\d{4}-\d{2}-\d{2}[Tt]\d{2}:\d{2}:\d{2}(\.\d+)?([Zz]|[+-]\d{2}:\d{2})$")
_TOP_LEVEL_KEYS = {
    "version", "claim_id", "created_at", "metric", "comparator", "threshold",
    "dataset", "seed", "producer", "model", "compute_envelope", "prior_hash",
    "notes", "metric_args",
}


def _schema_conformance_errors(m: dict) -> list[str]:
    errors: list[str] = []
    cid = m.get("claim_id")
    if isinstance(cid, str) and not _UUIDV7.match(cid):
        errors.append("claim_id must be a UUIDv7 (schema pattern: version nibble 7, variant 8/9/a/b)")
    ca = m.get("created_at")
    if isinstance(ca, str) and not _RFC3339.match(ca):
        errors.append("created_at must be an RFC 3339 date-time")
    metric = m.get("metric")
    if isinstance(metric, str) and not (1 <= len(metric) <= 256):
        errors.append("metric must be 1..256 characters")
    seed = m.get("seed")
    if seed is not None and (isinstance(seed, bool) or not isinstance(seed, int)):
        errors.append("seed must be an integer or null")
    ds = m.get("dataset")
    if isinstance(ds, dict):
        if isinstance(ds.get("id"), str) and len(ds["id"]) < 1:
            errors.append("dataset.id must be non-empty")
        for k in ds:
            if k not in ("id", "hash", "uri"):
                errors.append(f"dataset.{k}: unknown field (schema additionalProperties: false)")
    prod = m.get("producer")
    if isinstance(prod, dict):
        if isinstance(prod.get("id"), str) and len(prod["id"]) < 1:
            errors.append("producer.id must be non-empty")
        for k in prod:
            if k not in ("id", "signature"):
                errors.append(f"producer.{k}: unknown field (schema additionalProperties: false)")
    ph = m.get("prior_hash")
    if ph is not None and not (isinstance(ph, str) and re.fullmatch(r"[0-9a-fA-F]{64}", ph)):
        errors.append("prior_hash must be 64 hex characters")
    notes = m.get("notes")
    if notes is not None and not (isinstance(notes, str) and len(notes) <= 4096):
        errors.append("notes must be a string of at most 4096 characters")
    for k in m:
        if k not in _TOP_LEVEL_KEYS:
            errors.append(f"{k}: unknown top-level field (schema additionalProperties: false)")
    return errors


def evaluate_predicate(observed: float, comparator: str, threshold: float,
                       tolerance: float = 1e-9) -> bool:
    if comparator == ">=":
        return observed >= threshold
    if comparator == "<=":
        return observed <= threshold
    if comparator == ">":
        return observed > threshold
    if comparator == "<":
        return observed < threshold
    if comparator == "==":
        # Spec §5.1: equality is within a tolerance (default 1e-9, overridable
        # via metric_args.tolerance). Exact float equality was a footgun and did
        # not match the spec; this honors it.
        return abs(observed - threshold) < tolerance
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

    # Optional dataset-content check (spec §5.2 step 2). PRML does not
    # standardize a dataset preimage — dataset.hash is a producer-declared
    # content digest — so this is only meaningful when the verifier has the
    # exact bytes the producer hashed. For the common single-file case we
    # recompute a plain SHA-256 and refuse on mismatch. This makes step 2 real
    # for at least the Python reference instead of a spec MUST no impl honors.
    dpath = getattr(args, "dataset", None)
    if dpath:
        if not os.path.isfile(dpath):
            sys.stderr.write(f"verify: --dataset not a file: {dpath}\n")
            return EXIT_GUARD
        h = hashlib.sha256()
        with open(dpath, "rb") as fh:
            for chunk in iter(lambda: fh.read(1 << 20), b""):
                h.update(chunk)
        got = h.hexdigest()
        declared = m.get("dataset", {}).get("hash", "")
        if got != declared:
            print("DATASET MISMATCH")
            print(f"  declared:    {declared}")
            print(f"  recomputed:  {got}")
            print(f"  file:        {dpath}")
            return EXIT_GUARD
        print(f"dataset content verified: sha256:{got}")

    if args.observed is None:
        print(f"OK  hash verified  sha256:{recomputed}")
        print("(no --observed value given; predicate not evaluated)")
        return EXIT_PASS

    try:
        observed = float(args.observed)
    except ValueError:
        sys.stderr.write("verify: --observed must be a finite number\n")
        return EXIT_BAD
    _tol = 1e-9
    _ma = m.get("metric_args")
    if isinstance(_ma, dict) and isinstance(_ma.get("tolerance"), (int, float)):
        _tol = float(_ma["tolerance"])
    if evaluate_predicate(observed, m["comparator"], m["threshold"], _tol):
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
    sp.add_argument("--dataset", default=None,
                    help="path to the single-file dataset; recompute its SHA-256 and check it "
                         "matches dataset.hash (spec §5.2 step 2). Exit 11 on mismatch.")
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
