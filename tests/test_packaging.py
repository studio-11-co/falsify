"""Packaging and CLI-entry tests.

The unittest suite runs from the repository root, where every module is
importable whether or not the wheel ships it. falsify 0.5.1 shipped without
falsify_linkage.py for that reason: `falsify-engine linkage` failed with
ModuleNotFoundError and `falsify linkage` was not a subcommand. These tests
check the module list and the `falsify linkage` entry directly.
"""

from __future__ import annotations

import re
import subprocess
import sys
import tempfile
import tomllib
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PRML_CLI = REPO_ROOT / "falsify_prml.py"
ENGINE_CLI = REPO_ROOT / "falsify.py"

MANIFEST_YAML = """\
version: prml/0.1
claim_id: 01900000-0000-7000-8000-000000000000
created_at: '2026-05-01T12:00:00Z'
metric: accuracy
comparator: '>='
threshold: 0.85
dataset:
  id: unit-dataset
  hash: e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
seed: 42
producer:
  id: example.org
"""


def _run(cli: Path, args: list[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(cli), *args], cwd=cwd, capture_output=True, text=True
    )


class PyModulesTests(unittest.TestCase):
    def test_every_imported_root_module_is_shipped(self):
        with open(REPO_ROOT / "pyproject.toml", "rb") as fh:
            shipped = set(tomllib.load(fh)["tool"]["setuptools"]["py-modules"])
        root_modules = {p.stem for p in REPO_ROOT.glob("*.py")}
        pattern = re.compile(r"^\s*(?:import|from)\s+([A-Za-z_][A-Za-z0-9_]*)", re.M)
        missing = {}
        for mod in sorted(shipped):
            source = (REPO_ROOT / f"{mod}.py").read_text(encoding="utf-8")
            for name in pattern.findall(source):
                if name in root_modules and name not in shipped:
                    missing.setdefault(mod, set()).add(name)
        self.assertEqual(missing, {}, f"imported by a shipped module but not in py-modules: {missing}")


class LinkageEntryTests(unittest.TestCase):
    def test_help_lists_linkage(self):
        with tempfile.TemporaryDirectory() as tmp:
            proc = _run(PRML_CLI, ["--help"], Path(tmp))
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("linkage", proc.stdout)

    def test_linkage_help_is_forwarded(self):
        with tempfile.TemporaryDirectory() as tmp:
            proc = _run(PRML_CLI, ["linkage", "--help"], Path(tmp))
        self.assertEqual(proc.returncode, 0, proc.stderr)
        for word in ("start", "finish", "verify"):
            self.assertIn(word, proc.stdout)

    def test_error_matches_engine(self):
        with tempfile.TemporaryDirectory() as tmp:
            a = _run(PRML_CLI, ["linkage", "verify", "missing.yaml"], Path(tmp))
            b = _run(ENGINE_CLI, ["linkage", "verify", "missing.yaml"], Path(tmp))
        self.assertNotEqual(a.returncode, 0)
        self.assertEqual((a.returncode, a.stderr), (b.returncode, b.stderr))

    def test_start_finish_verify_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            (cwd / "claim.prml.yaml").write_text(MANIFEST_YAML, encoding="utf-8")
            (cwd / "result.json").write_text('{"accuracy": 0.9}\n', encoding="utf-8")
            steps = [
                ["linkage", "start", "claim.prml.yaml", "--run-id", "run-1",
                 "--environment", "unittest", "-o", "start.yaml"],
                ["linkage", "finish", "start.yaml", "--observed", "0.9",
                 "--result-file", "result.json", "--manifest", "claim.prml.yaml",
                 "-o", "final.yaml"],
                ["linkage", "verify", "final.yaml", "--start", "start.yaml",
                 "--manifest", "claim.prml.yaml"],
            ]
            for args in steps:
                proc = _run(PRML_CLI, args, cwd)
                self.assertEqual(proc.returncode, 0, f"{args[1]}: {proc.stdout}{proc.stderr}")


if __name__ == "__main__":
    unittest.main()
