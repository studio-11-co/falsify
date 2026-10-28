"""`--json` on `falsify verify`, `lock` and `hash`: one JSON object, same exit codes.

`status` separates the two cases that share exit 11 (NO_LOCK vs
DATASET_MISMATCH), so CI and agents need not parse text.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CLI = ROOT / "falsify_prml.py"
EX = ROOT / "examples" / "first-manifest"


def run(*args, cwd):
    r = subprocess.run([sys.executable, str(CLI), *args], capture_output=True, text=True, cwd=cwd)
    return r.returncode, (json.loads(r.stdout) if r.stdout.strip() else None)


class JsonOutput(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        for name in ("accuracy.prml.yaml", "accuracy.prml.prml.sha256", "eval_set.jsonl"):
            shutil.copy(EX / name, self.tmp)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_pass_fail_ok(self):
        self.assertEqual(run("verify", "accuracy.prml.yaml", "--observed", "0.934", "--json", cwd=self.tmp)[1]["status"], "PASS")
        code, d = run("verify", "accuracy.prml.yaml", "--observed", "0.5", "--json", cwd=self.tmp)
        self.assertEqual((code, d["status"], d["exit_code"]), (10, "FAIL", 10))
        code, d = run("verify", "accuracy.prml.yaml", "--json", cwd=self.tmp)
        self.assertEqual((code, d["status"], d["observed"]), (0, "OK", None))

    def test_tampered(self):
        f = Path(self.tmp) / "accuracy.prml.yaml"
        f.write_text(f.read_text().replace("threshold: 0.85", "threshold: 0.80"))
        code, d = run("verify", "accuracy.prml.yaml", "--json", cwd=self.tmp)
        self.assertEqual((code, d["status"]), (3, "TAMPERED"))
        self.assertNotEqual(d["recorded"], d["sha256"])

    def test_exit_11_cases_are_distinguished(self):
        Path(self.tmp, "other.jsonl").write_text("x\n")
        code, d = run("verify", "accuracy.prml.yaml", "--dataset", "other.jsonl", "--json", cwd=self.tmp)
        self.assertEqual((code, d["status"]), (11, "DATASET_MISMATCH"))
        os.remove(Path(self.tmp) / "accuracy.prml.prml.sha256")
        code, d = run("verify", "accuracy.prml.yaml", "--json", cwd=self.tmp)
        self.assertEqual((code, d["status"]), (11, "NO_LOCK"))

    def test_lock_and_hash(self):
        code, d = run("lock", "accuracy.prml.yaml", "--json", cwd=self.tmp)
        self.assertEqual((code, d["status"]), (0, "LOCKED"))
        code, h = run("hash", "accuracy.prml.yaml", "--json", cwd=self.tmp)
        self.assertEqual((code, h["status"], h["exit_code"]), (0, "OK", 0))
        self.assertEqual(d["sha256"], h["sha256"])

    def test_errors_are_json_on_every_command(self):
        # An invalid or unreadable manifest must still give one ERROR object on
        # stdout under --json (lock and hash printed only stderr text before).
        f = Path(self.tmp) / "accuracy.prml.yaml"
        f.write_text(f.read_text().replace("threshold: 0.85", "threshold: high"))
        for cmd in ("lock", "hash", "verify"):
            code, d = run(cmd, "accuracy.prml.yaml", "--json", cwd=self.tmp)
            self.assertEqual((code, d["status"], d["exit_code"]), (2, "ERROR", 2), cmd)
            self.assertIn("invalid manifest", d["error"])
        for cmd in ("lock", "hash", "verify"):
            code, d = run(cmd, "missing.prml.yaml", "--json", cwd=self.tmp)
            self.assertEqual((code, d["status"]), (2, "ERROR"), cmd)
            self.assertIn("cannot read", d["error"])


if __name__ == "__main__":
    unittest.main()
