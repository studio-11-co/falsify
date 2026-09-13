"""The §3.6 formal grammar reproduces every conformance vector and rejects
malformed canonical text. See spec/grammar/README.md.

This test imports the from-grammar emitter/recogniser (which does not import
PyYAML) and checks it against the same corpus the multi-language CI uses. If
it fails, either a vector changed (a specification-level event) or the
grammar no longer describes the reference canonicalizer.
"""
from __future__ import annotations

import hashlib
import json
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
GRAMMAR_DIR = REPO_ROOT / "spec" / "grammar"
sys.path.insert(0, str(GRAMMAR_DIR))

import check_grammar as cg  # noqa: E402

VECTORS = []
for rel in ("v0.1", "v0.2"):
    p = REPO_ROOT / "spec" / "test-vectors" / rel / "test-vectors.json"
    if p.exists():
        VECTORS += json.loads(p.read_text(encoding="utf-8"))

CANDIDATES_PATH = GRAMMAR_DIR / "candidate-vectors-2026-09-13.json"


class GrammarReproducesConformanceVectors(unittest.TestCase):
    def test_vector_corpus_present(self):
        self.assertEqual(len(VECTORS), 21, "13 v0.1 + 8 v0.2 vectors expected")

    def test_emit_matches_canonical_and_hash(self):
        for v in VECTORS:
            with self.subTest(v["id"]):
                produced = cg.emit(v["input"])
                self.assertEqual(produced, v["canonical"])
                self.assertEqual(hashlib.sha256(produced.encode("utf-8")).hexdigest(), v["hash"])

    def test_recogniser_accepts_every_vector(self):
        for v in VECTORS:
            with self.subTest(v["id"]):
                cg.recognize(v["canonical"])


class GrammarRejectsMalformedCanonicalText(unittest.TestCase):
    def setUp(self):
        self.base = VECTORS[0]["canonical"]

    def _reject(self, text, why):
        with self.assertRaises(cg.GrammarError, msg=why):
            cg.recognize(text)

    def test_crlf(self):
        self._reject(self.base.replace("\n", "\r\n"), "CRLF")

    def test_missing_final_lf(self):
        self._reject(self.base.rstrip("\n"), "missing final LF")

    def test_root_duplicate_key(self):
        self._reject(self.base.replace("seed: 42\n", "seed: 42\nseed: 42\n"), "duplicate root key")

    def test_root_key_order(self):
        self._reject(self.base.replace("threshold: 0.85\nversion: prml/0.1\n", "version: prml/0.1\nthreshold: 0.85\n"), "root order")

    def test_nested_duplicate_key(self):
        self._reject(self.base.replace("  id: imagenet-val-2012\n", "  id: imagenet-val-2012\n  id: imagenet-val-2012\n"), "nested duplicate")

    def test_integer_threshold_under_v01(self):
        self._reject(self.base.replace("threshold: 0.85", "threshold: 1"), "§3.5 float rule")

    def test_non_canonical_float(self):
        self._reject(self.base.replace("threshold: 0.85", "threshold: 0.850"), "shortest round-trip")

    def test_plain_where_quotes_required(self):
        self._reject(self.base.replace("comparator: '>='", "comparator: >="), "C5")

    def test_quoted_where_plain_required(self):
        self._reject(self.base.replace("metric: accuracy", "metric: 'accuracy'"), "C5")


class PlainScalarPredicate(unittest.TestCase):
    """The consequences spelled out in README §C5 — the cases three reference
    implementations got wrong."""

    def test_plain(self):
        for s in ("?x", ":x", "-x", "y", "n", "1e5", "0o17", "=x", "prml/0.1", "n/a-streaming", "e3b0c442", "üniversite", "it's"):
            with self.subTest(s):
                self.assertTrue(cg.is_plain(s))

    def test_single_quoted(self):
        for s in ("-", "?", "<<", "=", "1:30", "1_000", "0b101", "017", ".5", "5.", "2026-05-01", "yes", "null", "~", "", ">=", "a:", "x: y", "a #b"):
            with self.subTest(repr(s)):
                self.assertFalse(cg.is_plain(s))


class FloatRule(unittest.TestCase):
    def test_boundaries(self):
        cases = {0.0001: "0.0001", 1e-05: "1.0e-05", 1e-06: "1.0e-06", 1.5e-07: "1.5e-07",
                 1e15: "1000000000000000.0", 1e16: "1.0e+16", 1.0: "1.0", 90.0: "90.0",
                 5e-324: "5.0e-324", -0.5: "-0.5", -1e-05: "-1.0e-05", 0.0: "0.0"}
        for x, want in cases.items():
            with self.subTest(x):
                self.assertEqual(cg.render_float(x), want)

    def test_non_finite_has_no_production(self):
        for x in (float("inf"), float("-inf"), float("nan")):
            with self.assertRaises(ValueError):
                cg.render_float(x)


@unittest.skipUnless(CANDIDATES_PATH.exists(), "candidate vectors not present")
class GrammarReproducesCandidateBattery(unittest.TestCase):
    def test_all_candidates(self):
        cands = json.loads(CANDIDATES_PATH.read_text(encoding="utf-8"))
        self.assertGreaterEqual(len(cands), 80)
        for c in cands:
            with self.subTest(c["id"]):
                produced = cg.emit(c["input"])
                self.assertEqual(produced, c["canonical"])
                self.assertEqual(hashlib.sha256(produced.encode("utf-8")).hexdigest(), c["hash"])


if __name__ == "__main__":
    unittest.main()
