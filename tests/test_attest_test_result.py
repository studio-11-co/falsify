"""`falsify attest --as test-result`: in-toto Test Result v0.1 for one run.

The PRML manifest is the `configuration` (digest = PRML hash), so a policy can
require that a test ran against the exact bar that was locked. The command
refuses to attest when the manifest no longer matches its lock.
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
HASH = "9cb2a71b75355dd52d56ea79212a79442eec6ed512bc93c4bb25ff897c4b1005"
MODEL = "model=sha256:" + "ab" * 32


def run(*args, cwd, env=None):
    e = {k: v for k, v in os.environ.items() if not k.startswith("GITHUB_")}
    if env:
        e.update(env)
    return subprocess.run([sys.executable, str(CLI), *args], capture_output=True, text=True, cwd=cwd, env=e)


class TestResult(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        for name in ("accuracy.prml.yaml", "accuracy.prml.prml.sha256"):
            shutil.copy(EX / name, self.tmp)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def attest(self, *extra, env=None):
        return run("attest", "accuracy.prml.yaml", "--as", "test-result", *extra, cwd=self.tmp, env=env)

    def test_passed(self):
        r = self.attest("--observed", "0.934", "--subject", MODEL)
        self.assertEqual(r.returncode, 0, r.stderr)
        st = json.loads(r.stdout)
        self.assertEqual(st["predicateType"], "https://in-toto.io/attestation/test-result/v0.1")
        p = st["predicate"]
        self.assertEqual(p["result"], "PASSED")
        self.assertEqual(p["configuration"][0]["digest"]["sha256"], HASH)
        self.assertEqual(p["configuration"][0]["mediaType"], "application/vnd.prml+yaml")
        self.assertEqual(p["passedTests"], ["accuracy >= 0.85"])
        self.assertEqual(st["subject"], [{"name": "model", "digest": {"sha256": "ab" * 32}}])

    def test_failed_exits_10(self):
        r = self.attest("--observed", "0.5", "--subject", MODEL)
        self.assertEqual(r.returncode, 10)
        p = json.loads(r.stdout)["predicate"]
        self.assertEqual(p["result"], "FAILED")
        self.assertEqual(p["failedTests"], ["accuracy >= 0.85"])

    def test_tampered_manifest_is_not_attested(self):
        f = Path(self.tmp) / "accuracy.prml.yaml"
        f.write_text(f.read_text().replace("threshold: 0.85", "threshold: 0.80"))
        r = self.attest("--observed", "0.934", "--subject", MODEL)
        self.assertEqual(r.returncode, 3)
        self.assertEqual(r.stdout, "")
        self.assertIn("TAMPERED", r.stderr)

    def test_needs_a_lock(self):
        os.remove(Path(self.tmp) / "accuracy.prml.prml.sha256")
        self.assertEqual(self.attest("--observed", "0.934").returncode, 11)
        self.assertEqual(self.attest("--observed", "0.934", "--expected-hash", HASH).returncode, 0)

    def test_bad_inputs(self):
        self.assertEqual(self.attest().returncode, 2)
        self.assertEqual(self.attest("--observed=inf").returncode, 2)
        self.assertEqual(self.attest("--observed", "0.9", "--subject", "model=md5:abc").returncode, 2)

    def test_default_subject_is_the_dataset(self):
        r = self.attest("--observed", "0.934")
        self.assertEqual(r.returncode, 0)
        self.assertIn("--subject", r.stderr)
        import yaml
        ds = yaml.safe_load((Path(self.tmp) / "accuracy.prml.yaml").read_text())["dataset"]
        self.assertEqual(json.loads(r.stdout)["subject"], [{"name": ds["id"], "digest": {"sha256": ds["hash"]}}])

    def test_github_run_url(self):
        env = {"GITHUB_RUN_ID": "42", "GITHUB_REPOSITORY": "o/r", "GITHUB_SERVER_URL": "https://github.com"}
        r = self.attest("--observed", "0.934", "--subject", MODEL, env=env)
        self.assertEqual(json.loads(r.stdout)["predicate"]["url"], "https://github.com/o/r/actions/runs/42")

    def test_default_mode_unchanged(self):
        r = run("attest", "accuracy.prml.yaml", cwd=self.tmp)
        self.assertEqual(r.returncode, 0)
        self.assertEqual(json.loads(r.stdout)["predicateType"], "https://falsify.dev/prml/v0.1")


if __name__ == "__main__":
    unittest.main()
