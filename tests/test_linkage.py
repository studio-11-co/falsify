"""Tests for falsify_linkage (prml-linkage/0 draft reference implementation)."""

import hashlib
import unittest

import falsify
import falsify_linkage as fl

MANIFEST = {
    "version": "prml/0.1",
    "claim_id": "01900000-0000-7000-8000-000000000000",
    "metric": "accuracy",
    "threshold": 0.85,
    "comparator": ">=",
    "created_at": "2026-05-01T12:00:00Z",
    "dataset": {
        "id": "imagenet-val-2012",
        "hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    },
    "producer": {"id": "studio-11.co"},
    "seed": 42,
}

DIGEST = hashlib.sha256(b"raw result artifact").hexdigest()


def _manifest_hash() -> str:
    return hashlib.sha256(fl.canonicalize(MANIFEST).encode("utf-8")).hexdigest()


def _start(**kw):
    defaults = dict(
        manifest_hash=_manifest_hash(),
        run_id="run-0001",
        environment="unittest/darwin",
        dataset_hash=MANIFEST["dataset"]["hash"],
        started_at="2026-08-13T10:00:00Z",
    )
    defaults.update(kw)
    return fl.build_start(**defaults)


def _final(start=None, observed=0.90, exit_code=0, finished="2026-08-13T10:05:00Z"):
    start = start or _start()
    return fl.finalize(start, observed, DIGEST, exit_code, finished_at=finished)


class TestLinkage(unittest.TestCase):
    def test_canonicalization_parity_with_falsify(self):
        # Spec requirement: linkage hashes under the same canon rules as manifests.
        self.assertEqual(fl.canonicalize(MANIFEST), falsify._canonicalize(MANIFEST))

    def test_roundtrip_verifies_at_l2(self):
        start = _start()
        final = _final(start)
        report = fl.verify(final, start_record=start, manifest=MANIFEST)
        self.assertTrue(report["ok"], report["failures"])
        self.assertEqual(report["tier"], "L2")
        self.assertEqual(report["skipped"], [])

    def test_l1_without_start_record(self):
        report = fl.verify(_final(), manifest=MANIFEST)
        self.assertTrue(report["ok"], report["failures"])
        self.assertEqual(report["tier"], "L1")
        self.assertTrue(any("chain" in s for s in report["skipped"]))

    def test_tampered_observed_breaks_verdict(self):
        final = _final(observed=0.80, exit_code=0)  # claims pass but 0.80 < 0.85
        report = fl.verify(final, manifest=MANIFEST)
        self.assertFalse(report["ok"])
        self.assertEqual(report["failures"][0]["check"], "verdict-mismatch")

    def test_tampered_start_field_breaks_chain(self):
        start = _start()
        final = _final(start)
        tampered = dict(start)
        tampered["run"] = dict(start["run"], started_at="2026-08-13T09:00:00Z")
        report = fl.verify(final, start_record=tampered)
        self.assertFalse(report["ok"])
        self.assertTrue(all(f["check"] == "chain-broken" for f in report["failures"]))

    def test_chronology_violation(self):
        final = _final(finished="2026-08-13T09:59:59Z")  # before started_at
        report = fl.verify(final)
        self.assertFalse(report["ok"])
        self.assertEqual(report["failures"][0]["check"], "chronology")

    def test_dataset_mismatch_against_manifest(self):
        start = _start(dataset_hash="a" * 64)
        final = _final(start)
        report = fl.verify(final, start_record=start, manifest=MANIFEST)
        self.assertFalse(report["ok"])
        self.assertTrue(any(f["check"] == "dataset-mismatch" for f in report["failures"]))

    def test_unknown_field_is_malformed(self):
        final = _final()
        final["surprise"] = True
        report = fl.verify(final)
        self.assertFalse(report["ok"])
        self.assertEqual(report["failures"][0]["check"], "malformed")

    def test_error_exit_codes_skip_verdict_recompute(self):
        final = _final(exit_code=11)
        report = fl.verify(final, manifest=MANIFEST)
        self.assertTrue(report["ok"], report["failures"])
        self.assertTrue(any("verdict recompute" in s for s in report["skipped"]))

    def test_finalize_rejects_bad_start(self):
        with self.assertRaises(ValueError):
            fl.finalize({"linkage_version": "nope"}, 0.9, DIGEST, 0)

    def test_integer_observed_canonicalizes_as_float(self):
        # Spec float rule: observed is float64; integer values render as "x.0"
        final = _final(observed=1)
        self.assertIsInstance(final["result"]["observed"], float)
        self.assertIn("observed: 1.0", fl.canonicalize(final))

    def test_start_rejects_bad_hashes(self):
        with self.assertRaises(ValueError):
            _start(manifest_hash="xyz")
        with self.assertRaises(ValueError):
            _start(dataset_hash="short")


if __name__ == "__main__":
    unittest.main()
