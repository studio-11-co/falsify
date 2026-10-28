"""`falsify verify --observed` must reject non-finite values (exit 2).

float() accepts "inf"/"nan", and `inf >= threshold` would PASS every bar, so
the PRML CLI rejects them the way the JS and Rust reference CLIs do.
"""
from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CLI = ROOT / "falsify_prml.py"
SPEC = ROOT / "examples" / "first-manifest" / "accuracy.prml.yaml"


def verify(observed: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(CLI), "verify", str(SPEC), f"--observed={observed}"],
        capture_output=True, text=True, cwd=str(SPEC.parent),
    )


class VerifyObserved(unittest.TestCase):
    def test_finite_pass_and_fail(self) -> None:
        self.assertEqual(verify("0.934").returncode, 0)
        self.assertEqual(verify("0.5").returncode, 10)

    def test_non_finite_rejected(self) -> None:
        for bad in ("inf", "-inf", "Infinity", "nan", "NaN"):
            with self.subTest(observed=bad):
                r = verify(bad)
                self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
                self.assertIn("finite", r.stderr)

    def test_unparseable_rejected(self) -> None:
        self.assertEqual(verify("0.9abc").returncode, 2)


if __name__ == "__main__":
    unittest.main()
