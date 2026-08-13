"""Cross-language parity: falsify_linkage.py vs impl/js/linkage.js.

Spawns node with impl/js/linkage-parity-target.js per case. Skipped when
node is not available (matches the suite's existing skip pattern).
"""

import hashlib
import json
import shutil
import subprocess
import unittest
from pathlib import Path

import falsify_linkage as fl

ROOT = Path(__file__).resolve().parent.parent
TARGET = ROOT / "impl" / "js" / "linkage-parity-target.js"
NODE = shutil.which("node")

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


def _node(request: dict) -> dict:
    proc = subprocess.run(
        [NODE, str(TARGET)],
        input=json.dumps(request),
        capture_output=True,
        text=True,
        timeout=30,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"node target failed: {proc.stderr[:400]}")
    return json.loads(proc.stdout)


def _start():
    mh = hashlib.sha256(fl.canonicalize(MANIFEST).encode("utf-8")).hexdigest()
    return fl.build_start(
        manifest_hash=mh,
        run_id="run-0001",
        environment="parity/darwin",
        dataset_hash=MANIFEST["dataset"]["hash"],
        started_at="2026-08-13T10:00:00Z",
    )


@unittest.skipIf(NODE is None, "node not available")
class TestLinkageParity(unittest.TestCase):
    def test_canonical_bytes_and_hash_match_for_start_record(self):
        start = _start()
        js = _node({"mode": "canonical", "record": start})
        self.assertEqual(js["canonical"], fl.canonicalize(start))
        self.assertEqual(js["hash"], fl.linkage_hash(start))

    def test_canonical_parity_for_final_record_with_integer_observed(self):
        # The observed float rule is where languages diverge; lock it down.
        start = _start()
        final_py = fl.finalize(start, 1, DIGEST, 0, finished_at="2026-08-13T10:05:00Z")
        js = _node({"mode": "canonical", "record": final_py})
        self.assertIn("observed: 1.0", js["canonical"])
        self.assertEqual(js["canonical"], fl.canonicalize(final_py))
        self.assertEqual(js["hash"], fl.linkage_hash(final_py))

    def test_js_finalize_matches_python_finalize(self):
        start = _start()
        final_py = fl.finalize(start, 0.9, DIGEST, 0, finished_at="2026-08-13T10:05:00Z")
        js = _node(
            {
                "mode": "finalize",
                "start": start,
                "observed": 0.9,
                "digest": DIGEST,
                "exit_code": 0,
                "finished_at": "2026-08-13T10:05:00Z",
            }
        )
        self.assertEqual(js["final"], final_py)
        self.assertEqual(js["hash"], fl.linkage_hash(final_py))

    def test_verify_verdicts_agree_across_case_matrix(self):
        start = _start()
        good = fl.finalize(start, 0.9, DIGEST, 0, finished_at="2026-08-13T10:05:00Z")
        bad_verdict = fl.finalize(start, 0.8, DIGEST, 0, finished_at="2026-08-13T10:05:00Z")
        bad_chrono = fl.finalize(start, 0.9, DIGEST, 0, finished_at="2026-08-13T09:00:00Z")
        tampered_start = dict(start)
        tampered_start["run"] = dict(start["run"], started_at="2026-08-13T09:00:00Z")

        cases = [
            ("roundtrip", good, start, MANIFEST),
            ("no-start", good, None, MANIFEST),
            ("no-manifest", good, start, None),
            ("bad-verdict", bad_verdict, None, MANIFEST),
            ("bad-chronology", bad_chrono, None, None),
            ("broken-chain", good, tampered_start, None),
        ]
        for name, final, start_rec, manifest in cases:
            with self.subTest(case=name):
                py = fl.verify(final, start_record=start_rec, manifest=manifest)
                js = _node({"mode": "verify", "final": final, "start": start_rec, "manifest": manifest})
                self.assertEqual(js["ok"], py["ok"], name)
                self.assertEqual(js["tier"], py["tier"], name)
                self.assertEqual(
                    sorted(f["check"] for f in js["failures"]),
                    sorted(f["check"] for f in py["failures"]),
                    name,
                )


if __name__ == "__main__":
    unittest.main()
