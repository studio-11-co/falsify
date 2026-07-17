"""YAML parse-layer parity between the two implementations that actually parse
YAML manifests: the Python reference (falsify_prml) and impl/js (js-yaml
CORE_SCHEMA). Go and Rust parse only JSON test vectors, so the parse layer
lives only here — and the conformance suite feeds PRE-PARSED objects, so it
never exercises this layer. This test feeds identical YAML *text* through both
parsers and asserts identical canonical hashes, including the YAML-1.1 vs 1.2
boolean tokens (yes/no/on/off) that used to diverge (Python safe_load treated
them as booleans; js-yaml CORE keeps them strings). See load_manifest's
_core_loader.
"""
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)
import falsify_prml as fp  # noqa: E402
IMPL_JS = os.path.join(REPO, "impl", "js", "falsify.js")
# js-yaml is not vendored in impl/js; borrow the registry's node_modules if present.
REG_NM = os.path.abspath(os.path.join(REPO, "..", "falsify-registry", "node_modules"))

# Manifests whose scalar values, unquoted, are YAML-1.1 bool/null spellings.
# Under YAML 1.2 core (js-yaml) they stay strings; the Python reference must agree.
CASES = [
    ("on", 'version: prml/0.1\nclaim_id: 01900000-0000-7000-8000-000000000000\n'
           "created_at: '2026-05-01T12:00:00Z'\nmetric: accuracy\ncomparator: '>='\n"
           'threshold: 0.85\ndataset:\n  id: on\n'
           '  hash: e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855\n'
           'seed: 42\nproducer:\n  id: falsify.dev\n'),
    ("yes", 'version: prml/0.1\nclaim_id: 01900000-0000-7000-8000-000000000000\n'
            "created_at: '2026-05-01T12:00:00Z'\nmetric: yes\ncomparator: '>='\n"
            'threshold: 0.85\ndataset:\n  id: imagenet-val-2012\n'
            '  hash: e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855\n'
            'seed: 42\nproducer:\n  id: falsify.dev\n'),
    ("plain", 'version: prml/0.1\nclaim_id: 01900000-0000-7000-8000-000000000000\n'
              "created_at: '2026-05-01T12:00:00Z'\nmetric: accuracy\ncomparator: '>='\n"
              'threshold: 0.85\ndataset:\n  id: imagenet-val-2012\n'
              '  hash: e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855\n'
              'seed: 42\nproducer:\n  id: falsify.dev\n'),
]


def _js_hash(path):
    env = dict(os.environ)
    if os.path.isdir(REG_NM):
        env["NODE_PATH"] = REG_NM + os.pathsep + env.get("NODE_PATH", "")
    out = subprocess.run(["node", IMPL_JS, "hash", path],
                         capture_output=True, text=True, env=env)
    line = (out.stdout or out.stderr).strip()
    if "js-yaml" in line and "install" in line:
        return None  # js-yaml unavailable in this environment
    return line.split()[-1]


class YamlParseParityTests(unittest.TestCase):
    def test_python_treats_yaml12_core_bool_tokens_as_strings(self):
        for tok in ("on", "yes", "off", "no", "y", "n"):
            with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False) as f:
                f.write(f"metric: {tok}\n")
                path = f.name
            try:
                val = fp.load_manifest(path)["metric"]
            finally:
                os.unlink(path)
            self.assertIsInstance(val, str, f"{tok!r} must stay a string under YAML 1.2 core")
            self.assertEqual(val, tok)
        # true/false still bool, null still None
        for tok, want in (("true", True), ("false", False)):
            with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False) as f:
                f.write(f"metric: {tok}\n")
                path = f.name
            try:
                self.assertIs(fp.load_manifest(path)["metric"], want)
            finally:
                os.unlink(path)

    @unittest.skipUnless(shutil.which("node"), "node not available")
    def test_python_and_js_hash_identical_yaml_text(self):
        for name, text in CASES:
            with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False) as f:
                f.write(text)
                path = f.name
            try:
                ph = fp.manifest_hash(fp.load_manifest(path))
                jh = _js_hash(path)
            finally:
                os.unlink(path)
            if jh is None:
                self.skipTest("js-yaml not installed for impl/js")
            self.assertEqual(ph, jh, f"case {name!r}: Python {ph} != JS {jh}")


if __name__ == "__main__":
    unittest.main()
