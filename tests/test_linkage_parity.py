"""Cross-language parity: falsify_linkage.py vs the JS, Go and Rust ports.

Every available target speaks the same stdin/stdout JSON protocol
(modes: canonical | finalize | verify):

  JS   → node impl/js/linkage-parity-target.js
  Go   → <built binary> linkage-parity     (built once per test run)
  Rust → impl/rust/target/release/falsify-rs linkage-parity  (prebuilt)

Targets whose toolchain/binary is unavailable are skipped individually,
matching the suite's existing skip pattern.
"""

import hashlib
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

import falsify_linkage as fl

ROOT = Path(__file__).resolve().parent.parent

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

_GO_BUILD_DIR = None


def _go_binary():
    """Build the Go impl once per test run; return binary path or None."""
    global _GO_BUILD_DIR
    if shutil.which("go") is None:
        return None
    if _GO_BUILD_DIR is None:
        _GO_BUILD_DIR = tempfile.mkdtemp(prefix="falsify-go-parity-")
        out = Path(_GO_BUILD_DIR) / "falsify-go"
        proc = subprocess.run(
            ["go", "build", "-o", str(out), "."],
            cwd=ROOT / "impl" / "go",
            capture_output=True,
            text=True,
            timeout=120,
        )
        if proc.returncode != 0:
            return None
    out = Path(_GO_BUILD_DIR) / "falsify-go"
    return [str(out), "linkage-parity"] if out.exists() else None


def _targets():
    """Return {name: argv} for every available parity target."""
    targets = {}
    node = shutil.which("node")
    if node:
        targets["js"] = [node, str(ROOT / "impl" / "js" / "linkage-parity-target.js")]
    go_cmd = _go_binary()
    if go_cmd:
        targets["go"] = go_cmd
    rust_bin = ROOT / "impl" / "rust" / "target" / "release" / "falsify-rs"
    if rust_bin.exists():
        targets["rust"] = [str(rust_bin), "linkage-parity"]
    return targets


def _call(argv, request: dict) -> dict:
    proc = subprocess.run(
        argv,
        input=json.dumps(request),
        capture_output=True,
        text=True,
        timeout=60,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"target {argv[0]} failed: {proc.stderr[:400]}")
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


class TestLinkageParity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.targets = _targets()
        if not cls.targets:
            raise unittest.SkipTest("no parity targets available (node/go/rust missing)")

    def _each_target(self):
        for name, argv in self.targets.items():
            yield name, argv

    def test_canonical_bytes_and_hash_match_for_start_record(self):
        start = _start()
        for name, argv in self._each_target():
            with self.subTest(target=name):
                got = _call(argv, {"mode": "canonical", "record": start})
                self.assertEqual(got["canonical"], fl.canonicalize(start), name)
                self.assertEqual(got["hash"], fl.linkage_hash(start), name)

    def test_canonical_parity_for_final_record_with_integer_observed(self):
        # The observed float rule is where languages diverge; lock it down.
        start = _start()
        final_py = fl.finalize(start, 1, DIGEST, 0, finished_at="2026-08-13T10:05:00Z")
        for name, argv in self._each_target():
            with self.subTest(target=name):
                got = _call(argv, {"mode": "canonical", "record": final_py})
                self.assertIn("observed: 1.0", got["canonical"], name)
                self.assertEqual(got["canonical"], fl.canonicalize(final_py), name)
                self.assertEqual(got["hash"], fl.linkage_hash(final_py), name)

    def test_finalize_matches_python_finalize(self):
        start = _start()
        final_py = fl.finalize(start, 0.9, DIGEST, 0, finished_at="2026-08-13T10:05:00Z")
        for name, argv in self._each_target():
            with self.subTest(target=name):
                got = _call(
                    argv,
                    {
                        "mode": "finalize",
                        "start": start,
                        "observed": 0.9,
                        "digest": DIGEST,
                        "exit_code": 0,
                        "finished_at": "2026-08-13T10:05:00Z",
                    },
                )
                self.assertEqual(got["hash"], fl.linkage_hash(final_py), name)
                # Hash equality implies canonical-byte equality; the JSON
                # object comparison additionally pins field structure.
                self.assertEqual(
                    fl.canonicalize(got["final"]), fl.canonicalize(final_py), name
                )

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
        for name, argv in self._each_target():
            for case, final, start_rec, manifest in cases:
                with self.subTest(target=name, case=case):
                    py = fl.verify(final, start_record=start_rec, manifest=manifest)
                    got = _call(
                        argv,
                        {"mode": "verify", "final": final, "start": start_rec, "manifest": manifest},
                    )
                    self.assertEqual(got["ok"], py["ok"], f"{name}/{case}")
                    self.assertEqual(got["tier"], py["tier"], f"{name}/{case}")
                    self.assertEqual(
                        sorted(f["check"] for f in got["failures"]),
                        sorted(f["check"] for f in py["failures"]),
                        f"{name}/{case}",
                    )


if __name__ == "__main__":
    unittest.main()
