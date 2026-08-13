"""Tests for the `falsify conform` vector loader (RFC v0.2 P-04)."""

import unittest
from pathlib import Path

import falsify

VECTORS_DIR = Path(falsify.__file__).parent / "spec" / "test-vectors" / "v0.1"


class TestConformLoader(unittest.TestCase):
    def test_json_and_directory_formats_agree(self):
        from_json = falsify._conform_load_vectors(VECTORS_DIR / "test-vectors.json")
        from_dirs = falsify._conform_load_vectors(VECTORS_DIR / "vectors")
        self.assertEqual(len(from_json), 13)
        self.assertEqual(len(from_dirs), 13)
        by_id_json = {v["id"]: v for v in from_json}
        for v in from_dirs:
            ref = by_id_json[v["id"]]
            # canonical bytes and hash must be identical across formats
            self.assertEqual(v["canonical"], ref["canonical"], v["id"])
            self.assertEqual(v["hash"], ref["hash"], v["id"])

    def test_missing_path_raises(self):
        with self.assertRaises(ValueError):
            falsify._conform_load_vectors(VECTORS_DIR / "empty-nonexistent-dir")


if __name__ == "__main__":
    unittest.main()
