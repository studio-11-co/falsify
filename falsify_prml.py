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
    falsify attest <spec> [--as test-result]      emit an in-toto Statement (PRML or Test Result)
    falsify anchor <spec> [--sealed]              post to the registry, save the receipt files
    falsify receipt verify <spec> [--fetch]       verify the RFC 3161 token and Rekor entry offline
    falsify init <name> [--dataset FILE]          write a new manifest (UUIDv7, current time)
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

__version__ = "0.5.0"

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
    elif m.get("version") == "prml/0.2":
        # v0.2 `threshold` canonicalizes by VALUE, not by the spelling of the input
        # (RFC post-freeze clarification, 2026-09-13): an integral value with
        # |v| < 2**53 renders as an integer, anything else as a float (§3.6 C4).
        # So `1300.0` and `1300` are one manifest with one hash, and JavaScript —
        # whose JSON.parse and js-yaml cannot tell them apart — agrees with every
        # other implementation. 2**53 is the bound because above it the shortest
        # round-trip digits of an integral float can differ from its exact value.
        t = m.get("threshold")
        if isinstance(t, (int, float)) and not isinstance(t, bool):
            if isinstance(t, float) and t.is_integer() and abs(t) < 2**53:
                m["threshold"] = int(t)
            elif isinstance(t, int) and abs(t) >= 2**53:
                m["threshold"] = float(t)
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
    if not math.isfinite(observed):
        # float() accepts "inf"/"nan"; `inf >= threshold` would PASS every bar.
        # Reject like the JS and Rust reference CLIs (exit 2).
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


def new_uuid7() -> str:
    """RFC 9562 UUIDv7: 48-bit Unix time in ms, version 7, variant 10, random rest.

    (``uuid.uuid7`` exists only from Python 3.14; this package supports 3.11+.)
    """
    import secrets
    import time
    ms = time.time_ns() // 1_000_000
    b = bytearray(ms.to_bytes(6, "big") + secrets.token_bytes(10))
    b[6] = 0x70 | (b[6] & 0x0F)
    b[8] = 0x80 | (b[8] & 0x3F)
    h = b.hex()
    return f"{h[:8]}-{h[8:12]}-{h[12:16]}-{h[16:20]}-{h[20:]}"


def _file_sha256(path: str) -> str:
    d = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            d.update(chunk)
    return d.hexdigest()


_PLACEHOLDER_HASH = "REPLACE_WITH_64_LOWERCASE_HEX"


def cmd_init(args) -> int:
    out = args.name if args.name.endswith((".yaml", ".yml", ".json")) else args.name + ".prml.yaml"
    if os.path.exists(out):
        sys.stderr.write(f"init: {out} already exists\n")
        return EXIT_BAD
    parent = os.path.dirname(out)
    if parent and not os.path.isdir(parent):
        sys.stderr.write(f"init: directory {parent} does not exist\n")
        return EXIT_BAD
    ds_id, ds_hash = args.dataset_id or "your-dataset-id", _PLACEHOLDER_HASH
    if args.dataset:
        try:
            ds_hash = _file_sha256(args.dataset)
        except OSError as e:
            sys.stderr.write(f"init: cannot read dataset {args.dataset}: {e}\n")
            return EXIT_BAD
        ds_id = args.dataset_id or os.path.basename(args.dataset)
    from datetime import datetime, timezone
    created = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    m = {
        "version": "prml/0.1",
        "claim_id": new_uuid7(),
        "created_at": created,
        "metric": args.metric,
        "comparator": args.comparator,
        "threshold": args.threshold,
        "dataset": {"id": ds_id, "hash": ds_hash},
        "seed": args.seed,
        "producer": {"id": args.producer},
    }
    if out.endswith(".json"):
        text = json.dumps(m, indent=2, ensure_ascii=False) + "\n"
    else:
        text = (
            "version: prml/0.1\n"
            f"claim_id: {m['claim_id']}\n"
            f'created_at: "{created}"\n'
            f"metric: {json.dumps(args.metric, ensure_ascii=False)}\n"
            f'comparator: "{args.comparator}"\n'
            f"threshold: {args.threshold!r}\n"
            "dataset:\n"
            f"  id: {json.dumps(ds_id, ensure_ascii=False)}\n"
            f"  hash: {ds_hash}\n"
            f"seed: {args.seed}\n"
            "producer:\n"
            f"  id: {json.dumps(args.producer, ensure_ascii=False)}\n"
        )
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(text)
    print(f"wrote {out}")
    print(f"  claim_id:    {m['claim_id']} (UUIDv7)")
    print(f"  created_at:  {created}")
    print(f"  bar:         {args.metric} {args.comparator} {args.threshold!r}")
    if ds_hash == _PLACEHOLDER_HASH:
        print("  dataset.hash is a placeholder: rerun with --dataset <file>, or paste the 64-hex SHA-256")
    else:
        print(f"  dataset:     {ds_id}  sha256:{ds_hash}")
    if args.producer == "your-org-or-domain":
        print("  producer.id is a placeholder: set --producer <your-org-or-domain>")
    print(f"check the bar, then: falsify lock {out}")
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


TEST_RESULT_TYPE = "https://in-toto.io/attestation/test-result/v0.1"


def to_test_result_statement(manifest: dict, observed: float, subjects: list[dict],
                             url: str | None = None, config_name: str | None = None) -> dict:
    """in-toto Test Result (v0.1) Statement for one run against a locked PRML bar.

    ``configuration`` is the PRML manifest (digest = the PRML hash, media type
    application/vnd.prml+yaml), so a policy can require that the test ran
    against the exact bar that was locked. ``subjects`` are the artifacts tested
    (for example the model); the caller supplies them.
    """
    errors = validate_manifest(manifest)
    if errors:
        raise ValueError("invalid manifest: " + "; ".join(errors))
    if not math.isfinite(observed):
        raise ValueError("observed must be a finite number")
    h = manifest_hash(manifest)
    ma = manifest.get("metric_args")
    tol = float(ma["tolerance"]) if isinstance(ma, dict) and isinstance(ma.get("tolerance"), (int, float)) else 1e-9
    passed = evaluate_predicate(observed, manifest["comparator"], manifest["threshold"], tol)
    test = f"{manifest['metric']} {manifest['comparator']} {manifest['threshold']}"
    pred: dict = {
        "result": "PASSED" if passed else "FAILED",
        "configuration": [{
            "name": config_name or str(manifest["claim_id"]),
            "digest": {"sha256": h},
            "mediaType": "application/vnd.prml+yaml",
        }],
        "passedTests": [test] if passed else [],
        "failedTests": [] if passed else [test],
    }
    if url:
        pred["url"] = url
    return {
        "_type": "https://in-toto.io/Statement/v1",
        "subject": subjects,
        "predicateType": TEST_RESULT_TYPE,
        "predicate": pred,
    }


def _parse_subject(text: str) -> dict:
    name, sep, digest = text.rpartition("=")
    algo, _, hexd = digest.partition(":")
    if not sep or not name or algo != "sha256" or not re.fullmatch(r"[0-9a-f]{64}", hexd):
        raise ValueError(f"--subject must look like NAME=sha256:<64 hex>, got {text!r}")
    return {"name": name, "digest": {"sha256": hexd}}


def cmd_attest(args) -> int:
    try:
        m = load_manifest(args.spec)
    except (OSError, ValueError) as e:
        sys.stderr.write(f"attest: cannot read {args.spec}: {e}\n")
        return EXIT_BAD
    if args.as_ != "test-result":
        try:
            stmt = to_intoto_statement(m)
        except ValueError as e:
            sys.stderr.write(f"attest: {e}\n")
            return EXIT_BAD
        print(json.dumps(stmt, indent=2, ensure_ascii=False, sort_keys=True))
        return EXIT_PASS

    # --as test-result: one run against the locked bar.
    if args.observed is None:
        sys.stderr.write("attest --as test-result needs --observed <value>\n")
        return EXIT_BAD
    try:
        observed = float(args.observed)
    except ValueError:
        observed = math.nan
    if not math.isfinite(observed):
        sys.stderr.write("attest: --observed must be a finite number\n")
        return EXIT_BAD
    errors = validate_manifest(m)
    if errors:
        sys.stderr.write("attest: invalid manifest:\n  - " + "\n  - ".join(errors) + "\n")
        return EXIT_BAD
    h = manifest_hash(m)
    # Only attest a run against the bar that was locked: the hash must match
    # --expected-hash or the sidecar written by `falsify lock`.
    expected = args.expected_hash
    if expected is None:
        sidecar = _sidecar_path(args.spec)
        if not os.path.exists(sidecar):
            sys.stderr.write(f"attest: no --expected-hash and sidecar not found: {sidecar}\n"
                             f"        run `falsify lock {args.spec}` before the run.\n")
            return EXIT_GUARD
        with open(sidecar, "r", encoding="utf-8") as fh:
            expected = fh.read().strip()
    if expected != h:
        sys.stderr.write(f"attest: TAMPERED, recorded {expected}, recomputed {h}; no attestation written\n")
        return EXIT_TAMPERED
    try:
        subjects = [_parse_subject(x) for x in (args.subject or [])]
    except ValueError as e:
        sys.stderr.write(f"attest: {e}\n")
        return EXIT_BAD
    if not subjects:
        ds = m["dataset"]
        subjects = [{"name": str(ds["id"]), "digest": {"sha256": str(ds["hash"])}}]
        sys.stderr.write("attest: no --subject given; using the dataset as subject "
                         "(pass --subject model=sha256:<hex> for the model you tested)\n")
    url = args.url
    if url is None and os.environ.get("GITHUB_RUN_ID") and os.environ.get("GITHUB_REPOSITORY"):
        url = (f"{os.environ.get('GITHUB_SERVER_URL', 'https://github.com')}/"
               f"{os.environ['GITHUB_REPOSITORY']}/actions/runs/{os.environ['GITHUB_RUN_ID']}")
    stmt = to_test_result_statement(m, observed, subjects, url=url, config_name=os.path.basename(args.spec))
    print(json.dumps(stmt, indent=2, ensure_ascii=False, sort_keys=True))
    return EXIT_PASS if stmt["predicate"]["result"] == "PASSED" else EXIT_FAIL


def cmd_anchor(args) -> int:
    import falsify_receipt as fr
    try:
        m = load_manifest(args.spec)
    except (OSError, ValueError) as e:
        sys.stderr.write(f"anchor: cannot read {args.spec}: {e}\n")
        return EXIT_BAD
    errors = validate_manifest(m)
    if errors:
        sys.stderr.write("anchor: invalid manifest:\n  - " + "\n  - ".join(errors) + "\n")
        return EXIT_BAD
    h = manifest_hash(m)
    if args.sealed:
        print(f"anchoring {args.spec} sealed: the hash and timestamps become public, the text stays withheld")
    else:
        print(f"anchoring {args.spec}: the manifest text becomes public at {args.registry.rstrip('/')}/{h}")
    try:
        resp = fr.anchor(args.spec, h, registry=args.registry, handle=args.handle, sealed=args.sealed)
    except (fr.ReceiptError, OSError) as e:
        sys.stderr.write(f"anchor: {e}\n")
        return EXIT_BAD
    print(f"  sha256:     {h}")
    print(f"  permalink:  {resp.get('permalink')}")
    print(f"  timestamp:  {resp.get('timestamp')}" + ("  (already in the registry)" if resp.get("existing") else ""))
    tsa = resp.get("tsa") or {}
    rek = resp.get("rekor") or {}
    print(f"  RFC 3161:   {tsa.get('gen_time') or 'not issued (the registry retries; run `falsify receipt verify --fetch` later)'}")
    print(f"  Rekor:      {('log index ' + str(rek.get('log_index'))) if rek else 'not issued'}")
    for k, path in resp.get("_saved", {}).items():
        print(f"  saved {k + ':':10} {path}")
    print("next: falsify receipt verify " + args.spec)
    return EXIT_PASS


def cmd_receipt_verify(args) -> int:
    import falsify_receipt as fr
    try:
        m = load_manifest(args.spec)
    except (OSError, ValueError) as e:
        sys.stderr.write(f"receipt verify: cannot read {args.spec}: {e}\n")
        return EXIT_BAD
    errors = validate_manifest(m)
    if errors:
        sys.stderr.write("receipt verify: invalid manifest:\n  - " + "\n  - ".join(errors) + "\n")
        return EXIT_BAD
    h = manifest_hash(m)
    paths = fr.receipt_paths(args.spec)
    if args.fetch:
        try:
            fr.fetch_receipt(args.spec, h, registry=args.registry)
        except fr.ReceiptError as e:
            sys.stderr.write(f"receipt verify: {e}\n")
            return EXIT_BAD
    tsr_path = args.tsr or paths["tsr"]
    rekor_path = args.rekor or paths["rekor"]
    have_tsr, have_rekor = os.path.exists(tsr_path), os.path.exists(rekor_path)
    if not (have_tsr or have_rekor):
        sys.stderr.write(f"receipt verify: no receipt files ({tsr_path}, {rekor_path}); "
                         "run `falsify anchor` or add --fetch\n")
        return EXIT_BAD
    try:
        trust = fr.load_trust(args.trusted_root)
        result = {"manifest_sha256": h}
        if have_tsr:
            with open(tsr_path, "rb") as fh:
                result["rfc3161"] = fr.verify_tsr(fh.read(), h, trust)
        if have_rekor:
            with open(rekor_path, "rb") as fh:
                result["rekor"] = fr.verify_rekor(fh.read(), h, trust)
    except ImportError:
        sys.stderr.write('receipt verify needs the receipt extra: pip install "falsify[receipt]"\n')
        return EXIT_GUARD
    def _state(part):
        if part["ok"]:
            return "ok"
        # Inclusion proof checked but no pinned key for that log: not a failure, not a pass.
        if part.get("inclusion_ok") and part.get("checkpoint_signed") is None:
            return "partial"
        return "fail"

    states = [_state(result[k]) for k in ("rfc3161", "rekor") if k in result]
    if "fail" in states:
        status = "INVALID"
    elif "partial" in states:
        status = "PARTIAL"
    else:
        status = "VERIFIED"
    result["status"] = status
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True, default=str))
    else:
        print(f"manifest sha256: {h}")
        if "rfc3161" in result:
            r = result["rfc3161"]
            print(f"  RFC 3161: {'OK' if r['ok'] else 'FAILED'}  " + (f"time {r['gen_time']}" if r["ok"] else str(r["error"])))
        if "rekor" in result:
            r = result["rekor"]
            if r["ok"]:
                print(f"  Rekor:    OK  {r['origin']} index {r['log_index']} (inclusion proof + signed checkpoint)")
            else:
                print(f"  Rekor:    {'PARTIAL' if r.get('inclusion_ok') and r.get('checkpoint_signed') is None else 'FAILED'}  {r['error']}")
        if status == "VERIFIED":
            t = (result.get("rfc3161") or {}).get("gen_time")
            print(f"RECEIPT VERIFIED: these manifest bytes existed no later than {t}." if t
                  else "RECEIPT VERIFIED: these manifest bytes are in the transparency log.")
            print("It does not show that the run happened after that time, or that any reported result is true.")
        else:
            print(f"RECEIPT {status}")
    if status == "VERIFIED":
        return EXIT_PASS
    if status == "PARTIAL":
        return EXIT_GUARD
    return EXIT_TAMPERED


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

    sp = sub.add_parser("attest", help="emit an in-toto Statement: the PRML predicate, or a Test Result for one run")
    sp.add_argument("spec")
    sp.add_argument("--as", dest="as_", choices=["prml", "test-result"], default="prml",
                    help="prml (default): the locked bar as predicate; test-result: in-toto Test Result "
                         "v0.1 for one run, with the manifest as configuration")
    sp.add_argument("--observed", default=None, help="test-result: the observed metric value")
    sp.add_argument("--subject", action="append", default=None,
                    help="test-result: tested artifact as NAME=sha256:<hex> (repeatable; default: the dataset)")
    sp.add_argument("--url", default=None, help="test-result: link to the run (default in GitHub Actions: the run URL)")
    sp.add_argument("--expected-hash", dest="expected_hash", default=None,
                    help="test-result: locked hash to check against (default: the sidecar)")
    sp.set_defaults(func=cmd_attest)

    sp = sub.add_parser("anchor", help="post the manifest to a PRML registry and save the receipt files")
    sp.add_argument("spec")
    sp.add_argument("--registry", default="https://registry.falsify.dev")
    sp.add_argument("--handle", default=None, help="submitter handle shown on the registry")
    sp.add_argument("--sealed", action="store_true",
                    help="publish only the hash and timestamps; the manifest text stays withheld")
    sp.set_defaults(func=cmd_anchor)

    sp = sub.add_parser("receipt", help="work with registry receipts")
    rsub = sp.add_subparsers(dest="receipt_cmd")
    rp = rsub.add_parser("verify", help="verify the RFC 3161 token and Rekor entry for a manifest, offline")
    rp.add_argument("spec")
    rp.add_argument("--tsr", default=None, help="RFC 3161 token (default: <stem>.prml.tsr)")
    rp.add_argument("--rekor", default=None, help="Rekor entry JSON (default: <stem>.prml.rekor.json)")
    rp.add_argument("--fetch", action="store_true", help="download the token and log entry from the registry first")
    rp.add_argument("--registry", default="https://registry.falsify.dev")
    rp.add_argument("--trusted-root", dest="trusted_root", default=None,
                    help="Sigstore trusted_root.json to use instead of the pinned TSA root and log key")
    rp.add_argument("--json", action="store_true", help="machine-readable output")
    rp.set_defaults(func=cmd_receipt_verify)

    sp = sub.add_parser("init", help="write a new manifest (UUIDv7 claim_id, current created_at)")
    sp.add_argument("name", help="output path; .prml.yaml is added unless it ends in .yaml/.yml/.json")
    sp.add_argument("--dataset", default=None, help="dataset file: its SHA-256 becomes dataset.hash")
    sp.add_argument("--dataset-id", dest="dataset_id", default=None, help="dataset.id (default: the file name)")
    sp.add_argument("--metric", default="accuracy")
    sp.add_argument("--comparator", default=">=", choices=[">=", "<=", ">", "<", "=="])
    sp.add_argument("--threshold", type=float, default=0.90)
    sp.add_argument("--seed", type=int, default=42)
    sp.add_argument("--producer", default="your-org-or-domain", help="producer.id")
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
