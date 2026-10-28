"""`falsify init`: a new manifest that can be locked as written.

Before 0.5.0 init wrote a skeleton with a placeholder claim_id and a fixed
2026-01-01 created_at, so `lock` failed until both were edited by hand and
nothing said how to produce a UUIDv7.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CLI = ROOT / "falsify_prml.py"
sys.path.insert(0, str(ROOT))
import falsify_prml as fp  # noqa: E402

UUID7 = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-7[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$")


def run(*args, cwd):
    return subprocess.run([sys.executable, str(CLI), *args], capture_output=True, text=True, cwd=cwd)


class Init(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        Path(self.tmp, "eval.jsonl").write_bytes(b'{"q":"a"}\n')

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_uuid7_shape_and_order(self):
        a = fp.new_uuid7()
        time.sleep(0.002)
        b = fp.new_uuid7()
        self.assertRegex(a, UUID7)
        self.assertLess(a[:13], b[:13])  # time-ordered prefix
        ms = int(a.replace("-", "")[:12], 16)
        self.assertLess(abs(ms / 1000 - time.time()), 60)

    def test_init_with_dataset_locks_as_written(self):
        r = run("init", "acc", "--dataset", "eval.jsonl", "--producer", "acme.example", cwd=self.tmp)
        self.assertEqual(r.returncode, 0, r.stderr)
        m = fp.load_manifest(os.path.join(self.tmp, "acc.prml.yaml"))
        self.assertRegex(m["claim_id"], UUID7)
        created = datetime.strptime(m["created_at"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        self.assertLess(abs((datetime.now(timezone.utc) - created).total_seconds()), 120)
        self.assertEqual(m["dataset"]["id"], "eval.jsonl")
        self.assertEqual(m["dataset"]["hash"], fp._file_sha256(os.path.join(self.tmp, "eval.jsonl")))
        self.assertEqual(fp.validate_manifest(m), [])
        self.assertEqual(run("lock", "acc.prml.yaml", cwd=self.tmp).returncode, 0)

    def test_json_output(self):
        r = run("init", "c.json", "--dataset", "eval.jsonl", cwd=self.tmp)
        self.assertEqual(r.returncode, 0, r.stderr)
        json.loads(Path(self.tmp, "c.json").read_text())
        self.assertEqual(run("lock", "c.json", cwd=self.tmp).returncode, 0)

    def test_placeholder_hash_is_reported_and_lock_refuses(self):
        r = run("init", "p", cwd=self.tmp)
        self.assertEqual(r.returncode, 0)
        self.assertIn("--dataset", r.stdout)
        self.assertEqual(run("lock", "p.prml.yaml", cwd=self.tmp).returncode, 2)

    def test_missing_directory_is_a_clean_error(self):
        r = run("init", "nodir/x", cwd=self.tmp)
        self.assertEqual(r.returncode, 2)
        self.assertIn("does not exist", r.stderr)
        self.assertNotIn("Traceback", r.stderr)

    def test_refuses_to_overwrite(self):
        self.assertEqual(run("init", "x", cwd=self.tmp).returncode, 0)
        self.assertEqual(run("init", "x", cwd=self.tmp).returncode, 2)


if __name__ == "__main__":
    unittest.main()
