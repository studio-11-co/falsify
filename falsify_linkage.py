"""Reference implementation of prml-linkage/0 (draft).

Spec: spec/linkage/prml-linkage-0.md. Non-normative draft; the format may
change until draft 0 is frozen.

Canonicalization intentionally mirrors falsify._canonicalize so that a
linkage record hashes under the same rules as a PRML manifest. The parity
is asserted by tests/test_linkage.py rather than by importing falsify.py,
so this module stays dependency-free beyond PyYAML.
"""

from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from typing import Any, Optional

import yaml

LINKAGE_VERSION = "prml-linkage/0"

START_FIELDS = {"linkage_version", "manifest_hash", "receipt", "run"}
FINAL_FIELDS = START_FIELDS | {"start_hash", "result"}
RUN_FIELDS = {"id", "started_at", "environment", "model_version", "dataset_hash"}
RESULT_FIELDS = {"observed", "digest", "exit_code", "finished_at"}
VALID_EXIT_CODES = {0, 3, 10, 11}

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def canonicalize(record: Any) -> str:
    """Stable YAML rendering, identical rules to falsify._canonicalize."""
    return yaml.safe_dump(
        record,
        sort_keys=True,
        default_flow_style=False,
        allow_unicode=True,
        width=4096,
    )


def linkage_hash(record: dict) -> str:
    return hashlib.sha256(canonicalize(record).encode("utf-8")).hexdigest()


def _parse_rfc3339(value: str) -> datetime:
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        raise ValueError(f"timestamp lacks timezone: {value!r}")
    return dt.astimezone(timezone.utc)


def build_start(
    manifest_hash: str,
    run_id: str,
    environment: str,
    dataset_hash: str,
    *,
    receipt: Optional[str] = None,
    model_version: Optional[str] = None,
    started_at: Optional[str] = None,
) -> dict:
    """Create a start record at run start. `started_at` defaults to now (UTC)."""
    if not _SHA256_RE.match(manifest_hash):
        raise ValueError("manifest_hash must be 64 lowercase hex chars")
    if not _SHA256_RE.match(dataset_hash):
        raise ValueError("dataset_hash must be 64 lowercase hex chars")
    if started_at is None:
        # Full microsecond precision: sub-second runs must still satisfy
        # the spec's strict started_at < finished_at chronology.
        started_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    _parse_rfc3339(started_at)
    return {
        "linkage_version": LINKAGE_VERSION,
        "manifest_hash": manifest_hash,
        "receipt": receipt,
        "run": {
            "id": run_id,
            "started_at": started_at,
            "environment": environment,
            "model_version": model_version,
            "dataset_hash": dataset_hash,
        },
    }


def finalize(
    start_record: dict,
    observed: float,
    result_digest: str,
    exit_code: int,
    *,
    finished_at: Optional[str] = None,
) -> dict:
    """Create the final record from a start record plus the run result."""
    problems = _validate_shape(start_record, final=False)
    if problems:
        raise ValueError(f"invalid start record: {problems}")
    if exit_code not in VALID_EXIT_CODES:
        raise ValueError(f"exit_code must be one of {sorted(VALID_EXIT_CODES)}")
    if not _SHA256_RE.match(result_digest):
        raise ValueError("result digest must be 64 lowercase hex chars")
    if finished_at is None:
        finished_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    _parse_rfc3339(finished_at)
    final = {k: start_record[k] for k in START_FIELDS}
    final["run"] = dict(start_record["run"])
    final["start_hash"] = linkage_hash(start_record)
    final["result"] = {
        # Spec float rule: observed is float64; integer values render as "x.0"
        "observed": float(observed),
        "digest": result_digest,
        "exit_code": exit_code,
        "finished_at": finished_at,
    }
    return final


def _validate_shape(record: dict, *, final: bool) -> list[str]:
    problems: list[str] = []
    expected = FINAL_FIELDS if final else START_FIELDS
    if not isinstance(record, dict):
        return ["record is not a mapping"]
    if record.get("linkage_version") != LINKAGE_VERSION:
        problems.append(f"linkage_version must be {LINKAGE_VERSION!r}")
    missing = expected - set(record)
    extra = set(record) - expected
    if missing:
        problems.append(f"missing fields: {sorted(missing)}")
    if extra:
        problems.append(f"unknown fields: {sorted(extra)}")
    run = record.get("run")
    if not isinstance(run, dict):
        problems.append("run is not a mapping")
    else:
        if set(run) != RUN_FIELDS:
            problems.append(
                f"run fields must be exactly {sorted(RUN_FIELDS)}, got {sorted(run)}"
            )
        dh = run.get("dataset_hash")
        if not (isinstance(dh, str) and _SHA256_RE.match(dh)):
            problems.append("run.dataset_hash must be 64 lowercase hex chars")
        try:
            _parse_rfc3339(str(run.get("started_at")))
        except Exception:
            problems.append("run.started_at is not RFC 3339")
    mh = record.get("manifest_hash")
    if not (isinstance(mh, str) and _SHA256_RE.match(mh)):
        problems.append("manifest_hash must be 64 lowercase hex chars")
    if final:
        sh = record.get("start_hash")
        if not (isinstance(sh, str) and _SHA256_RE.match(sh)):
            problems.append("start_hash must be 64 lowercase hex chars")
        result = record.get("result")
        if not isinstance(result, dict):
            problems.append("result is not a mapping")
        else:
            if set(result) != RESULT_FIELDS:
                problems.append(
                    f"result fields must be exactly {sorted(RESULT_FIELDS)}, got {sorted(result)}"
                )
            if result.get("exit_code") not in VALID_EXIT_CODES:
                problems.append(f"result.exit_code must be one of {sorted(VALID_EXIT_CODES)}")
            dg = result.get("digest")
            if not (isinstance(dg, str) and _SHA256_RE.match(dg)):
                problems.append("result.digest must be 64 lowercase hex chars")
            try:
                _parse_rfc3339(str(result.get("finished_at")))
            except Exception:
                problems.append("result.finished_at is not RFC 3339")
    return problems


_COMPARATORS = {
    ">=": lambda a, b: a >= b,
    ">": lambda a, b: a > b,
    "<=": lambda a, b: a <= b,
    "<": lambda a, b: a < b,
    "==": lambda a, b: a == b,
}


def verify(
    final_record: dict,
    *,
    start_record: Optional[dict] = None,
    manifest: Optional[dict] = None,
    manifest_hash: Optional[str] = None,
) -> dict:
    """Verify a final linkage record per spec §4.

    Returns {"ok": bool, "tier": "L1"|"L2", "failures": [...], "skipped": [...]}.
    Tier L3 (anchored) cannot be established offline by this function alone;
    callers holding anchor evidence check §4.8 themselves.
    """
    failures: list[dict] = []
    skipped: list[str] = []

    problems = _validate_shape(final_record, final=True)
    if problems:
        return {
            "ok": False,
            "tier": None,
            "failures": [{"check": "malformed", "detail": p} for p in problems],
            "skipped": [],
        }

    tier = "L1"
    if start_record is not None:
        tier = "L2"
        if linkage_hash(start_record) != final_record["start_hash"]:
            failures.append({"check": "chain-broken", "detail": "hash(start) != start_hash"})
        else:
            for key in START_FIELDS:
                if start_record.get(key) != final_record.get(key):
                    failures.append(
                        {"check": "chain-broken", "detail": f"field {key!r} differs between start and final"}
                    )
    else:
        skipped.append("chain (no start record supplied)")

    started = _parse_rfc3339(final_record["run"]["started_at"])
    finished = _parse_rfc3339(final_record["result"]["finished_at"])
    if not started < finished:
        failures.append({"check": "chronology", "detail": "started_at is not before finished_at"})

    if manifest is not None and manifest_hash is None:
        manifest_hash = hashlib.sha256(canonicalize(manifest).encode("utf-8")).hexdigest()

    if manifest_hash is not None:
        if final_record["manifest_hash"] != manifest_hash:
            failures.append({"check": "manifest-mismatch", "detail": "manifest_hash differs"})
    else:
        skipped.append("manifest hash (no manifest supplied)")

    if manifest is not None:
        m_dataset = (manifest.get("dataset") or {}).get("hash")
        if final_record["run"]["dataset_hash"] != m_dataset:
            failures.append({"check": "dataset-mismatch", "detail": "run.dataset_hash != manifest dataset.hash"})
        comparator = manifest.get("comparator")
        threshold = manifest.get("threshold")
        exit_code = final_record["result"]["exit_code"]
        if comparator in _COMPARATORS and isinstance(threshold, (int, float)) and exit_code in (0, 10):
            passed = _COMPARATORS[comparator](final_record["result"]["observed"], threshold)
            expected = 0 if passed else 10
            if exit_code != expected:
                failures.append(
                    {"check": "verdict-mismatch", "detail": f"observed vs threshold implies exit {expected}, record says {exit_code}"}
                )
        elif exit_code in (3, 11):
            skipped.append("verdict recompute (error exit code)")
    else:
        skipped.append("dataset + verdict (no manifest supplied)")

    return {"ok": not failures, "tier": tier, "failures": failures, "skipped": skipped}
