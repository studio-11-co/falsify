"""Negative-conformance tests for PRML — inputs every impl MUST reject.

Each vector in spec/test-vectors/reject/reject-vectors.json is a manifest that
is structurally complete but carries a control / non-portable character (C0/C1,
U+007F, U+2028/U+2029, or U+FEFF) in a string field. The PRML reference
contract is that such a manifest MUST NOT lock — `validate_manifest` returns at
least one error and the CLI exits non-zero — rather than silently hashing a
non-portable manifest.

This guards the cross-impl control-char reject rule shipped in v0.3.6 against
silent regression: if a future change drops the rule, the manifest would lock
again and these tests would catch it. The positive suites (test_prml_vectors)
prove clean manifests still lock; together they prove the rule is *specific*.

CI failure here is a specification-level event, not a code-quality nit.
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
VECTORS_PATH = REPO_ROOT / "spec" / "test-vectors" / "reject" / "reject-vectors.json"

sys.path.insert(0, str(REPO_ROOT))
import falsify_prml  # noqa: E402


def _load_vectors():
    if not VECTORS_PATH.exists():
        return None
    return json.loads(VECTORS_PATH.read_text(encoding="utf-8"))


VECTORS = _load_vectors() or []

# A clean manifest used as a positive control, so a vacuous "everything errors"
# bug cannot make this suite pass trivially.
CLEAN = {
    "version": "prml/0.1",
    "claim_id": "01900000-0000-7000-8000-000000000000",
    "created_at": "2026-05-01T12:00:00Z",
    "metric": "accuracy",
    "comparator": ">=",
    "threshold": 0.85,
    "dataset": {"id": "imagenet-val-2012",
                "hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"},
    "seed": 42,
    "producer": {"id": "studio-11.co"},
}


class RejectVectorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not VECTORS:
            raise unittest.SkipTest(f"reject vectors not present: {VECTORS_PATH}")

    def test_vector_count(self):
        """The reject suite ships 14 vectors: 9 control-char (RJ-001..007 values +
        RJ-013/014 keys) + 5 structural (RJ-008..012). Adding more is fine;
        dropping below means a guard was removed."""
        self.assertGreaterEqual(len(VECTORS), 14, f"Expected >=14 reject vectors, got {len(VECTORS)}")
        cats = {v["category"] for v in VECTORS}
        self.assertIn("control-char", cats)
        self.assertIn("structural", cats)

    def test_positive_control_clean_manifest_validates(self):
        """The clean control manifest MUST pass validation — otherwise the reject
        assertions below could be passing vacuously."""
        self.assertEqual(falsify_prml.validate_manifest(CLEAN), [],
                         "clean control manifest unexpectedly rejected — reject suite would be vacuous")

    def test_control_char_vectors_carry_a_forbidden_char(self):
        """Sanity: every control-char vector actually carries a forbidden codepoint
        somewhere in its input — in a value OR a key — so the data file can't
        silently rot into clean inputs. (Structural vectors are malformed in other
        ways and are exempt.)"""
        def has_forbidden(obj):
            bad = lambda s: any(ord(c) < 0x20 or 0x7f <= ord(c) <= 0x9f
                                or ord(c) in (0x2028, 0x2029, 0xfeff) for c in s)
            if isinstance(obj, str):
                return bad(obj)
            if isinstance(obj, dict):
                return any(bad(k) or has_forbidden(v) for k, v in obj.items())
            if isinstance(obj, (list, tuple)):
                return any(has_forbidden(x) for x in obj)
            return False
        for v in VECTORS:
            if v["category"] != "control-char" or "input" not in v:
                continue
            self.assertTrue(has_forbidden(v["input"]),
                            f"{v['id']} is control-char but its input has no forbidden char")


def _expected_phrasings(vector):
    """`expect` may be a list when conformant impls word one refusal differently."""
    e = vector["expect"]
    return [e] if isinstance(e, str) else list(e)


def _reject_reasons(vector):
    """Return the refusal messages for a vector, whichever layer catches it.

    Two defect classes cannot be expressed as a parsed dict at all: a duplicate
    key has already collapsed to last-wins by the time a dict exists, and `.inf`
    has no JSON literal. Those vectors carry `raw` manifest text and must be
    refused at the LOAD layer, so they are driven through load_manifest.
    """
    if "raw" not in vector:
        return falsify_prml.validate_manifest(vector["input"])
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, f"{vector['id']}.{vector.get('ext', 'yaml')}")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(vector["raw"])
        try:
            loaded = falsify_prml.load_manifest(path)
        except (ValueError, OSError) as e:
            return [str(e)]
        return falsify_prml.validate_manifest(loaded)


def _make_reject_test(vector):
    def test(self):
        errors = _reject_reasons(vector)
        self.assertTrue(
            errors,
            f"{vector['id']} ({vector['title']}) was ACCEPTED — it must be rejected.\n"
            f"  reason: {vector['reason']}",
        )
        # The rejection must cite the SPECIFIC rule, not some unrelated error.
        wanted = _expected_phrasings(vector)
        self.assertTrue(
            any(w in e for w in wanted for e in errors),
            f"{vector['id']} was rejected, but not for the expected reason "
            f"{wanted!r}; errors={errors}",
        )

    test.__doc__ = f"{vector['id']}: {vector['title']} is rejected ({vector['category']})"
    return test


for _v in VECTORS:
    setattr(RejectVectorTests, f"test_reject_{_v['id'].replace('-', '_')}", _make_reject_test(_v))


class HashCommandRejectsTests(unittest.TestCase):
    """The `hash` CLI command MUST reject the same inputs `lock`/`verify` do.

    `hash` is the most likely embed entry point, yet it historically skipped
    `validate_manifest` (unlike lock/verify and the Go/Rust impls) and would
    print a hash for a non-portable manifest — a silent, unverifiable
    commitment. This locks that gap shut.
    """

    @classmethod
    def setUpClass(cls):
        if not VECTORS:
            raise unittest.SkipTest(f"reject vectors not present: {VECTORS_PATH}")

    def _hash_exit(self, manifest=None, raw=None, ext="json") -> int:
        """Exit code of `hash` for a manifest given either as a dict or as raw text.

        Raw text is needed for the defects a dict cannot carry — a duplicate key
        collapses before a dict exists, and `.inf` has no JSON literal.
        """
        import contextlib
        import io

        fd, path = tempfile.mkstemp(suffix=f".prml.{ext}")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                fh.write(raw) if raw is not None else json.dump(manifest, fh)
            with contextlib.redirect_stderr(io.StringIO()), \
                 contextlib.redirect_stdout(io.StringIO()):
                return falsify_prml.main(["hash", path])
        finally:
            os.unlink(path)

    def test_clean_manifest_hashes(self):
        self.assertEqual(self._hash_exit(CLEAN), 0,
                         "the clean positive-control manifest must hash (exit 0)")

    def test_reject_vectors_are_not_hashed(self):
        for v in VECTORS:
            with self.subTest(vector=v["id"]):
                code = (self._hash_exit(raw=v["raw"], ext=v.get("ext", "yaml"))
                        if "raw" in v else self._hash_exit(v["input"]))
                self.assertNotEqual(
                    code, 0,
                    f"{v['id']} ({v['title']}) was HASHED — `hash` must reject it "
                    f"(reason: {v['reason']})",
                )


if __name__ == "__main__":
    unittest.main()
