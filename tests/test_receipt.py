"""`falsify anchor` and `falsify receipt verify` (falsify_receipt.py).

Fixtures are a real registry.falsify.dev record (hash af0bfb6d…, anchored
23 Aug 2026): the manifest, its RFC 3161 token from Sigstore's TSA and its
Rekor v2 entry. Verification is fully offline against the pinned trust
anchors. The anchor test runs against a local mock registry.
"""
from __future__ import annotations

import base64
import http.server
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CLI = ROOT / "falsify_prml.py"
FIX = Path(__file__).resolve().parent / "fixtures" / "receipt"
HASH = "af0bfb6d39b17e3ba8520b743043ff3d7cd303a14b02d526d9a5de9ed04b2375"

try:
    import rfc3161_client  # noqa: F401
    import cryptography  # noqa: F401
    HAVE_EXTRA = True
except ImportError:
    HAVE_EXTRA = False

sys.path.insert(0, str(ROOT))
import falsify_receipt as fr  # noqa: E402


def run(*args, cwd):
    return subprocess.run([sys.executable, str(CLI), *args], capture_output=True, text=True, cwd=cwd)


class ReceiptBase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        for f in FIX.iterdir():
            shutil.copy(f, self.tmp)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)


class InclusionProof(unittest.TestCase):
    def test_real_proof_and_a_flipped_hash(self):
        entry = json.loads((FIX / "claim.prml.rekor.json").read_text())["entry"]
        ip = entry["inclusionProof"]
        body = base64.b64decode(entry["canonicalizedBody"])
        import hashlib
        leaf = hashlib.sha256(b"\x00" + body).digest()
        proof = [base64.b64decode(h) for h in ip["hashes"]]
        root = base64.b64decode(ip["rootHash"])
        idx, size = int(ip["logIndex"]), int(ip["treeSize"])
        self.assertTrue(fr._inclusion_ok(idx, size, leaf, proof, root))
        bad = list(proof)
        bad[3] = bytes(32)
        self.assertFalse(fr._inclusion_ok(idx, size, leaf, bad, root))
        self.assertFalse(fr._inclusion_ok(idx + 1, size, leaf, proof, root))

    def test_receipt_paths(self):
        p = fr.receipt_paths("dir/accuracy.prml.yaml")
        self.assertEqual(p["tsr"], "dir/accuracy.prml.tsr")
        self.assertEqual(fr.receipt_paths("x.json")["rekor"], "x.prml.rekor.json")


@unittest.skipUnless(HAVE_EXTRA, 'needs the receipt extra: pip install "falsify[receipt]"')
class ReceiptVerify(ReceiptBase):
    def test_verified(self):
        r = run("receipt", "verify", "claim.prml.yaml", cwd=self.tmp)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("RECEIPT VERIFIED", r.stdout)
        self.assertIn("2026-08-23T05:43:56", r.stdout)
        self.assertIn("does not show", r.stdout)

    def test_json(self):
        r = run("receipt", "verify", "claim.prml.yaml", "--json", cwd=self.tmp)
        self.assertEqual(r.returncode, 0, r.stderr)
        d = json.loads(r.stdout)
        self.assertEqual(d["status"], "VERIFIED")
        self.assertTrue(d["rfc3161"]["ok"] and d["rekor"]["ok"] and d["rekor"]["checkpoint_signed"])

    def test_tampered_manifest(self):
        p = Path(self.tmp) / "claim.prml.yaml"
        text = p.read_text()
        self.assertIn("threshold:", text)
        lines = [("threshold: 0.12345" if ln.startswith("threshold:") else ln) for ln in text.splitlines()]
        p.write_text("\n".join(lines) + "\n")
        r = run("receipt", "verify", "claim.prml.yaml", cwd=self.tmp)
        self.assertEqual(r.returncode, 3, r.stdout + r.stderr)
        self.assertIn("not the manifest hash", r.stdout)

    def test_corrupted_token(self):
        t = Path(self.tmp) / "claim.prml.tsr"
        b = bytearray(t.read_bytes())
        b[-20] ^= 0xFF
        t.write_bytes(bytes(b))
        os.remove(Path(self.tmp) / "claim.prml.rekor.json")
        r = run("receipt", "verify", "claim.prml.yaml", cwd=self.tmp)
        self.assertEqual(r.returncode, 3, r.stdout + r.stderr)

    def test_unknown_log_is_partial(self):
        trust = fr.load_trust()
        trust["log_keys"] = {}
        res = fr.verify_rekor((FIX / "claim.prml.rekor.json").read_bytes(), HASH, trust)
        self.assertTrue(res["inclusion_ok"])
        self.assertIsNone(res["checkpoint_signed"])
        self.assertFalse(res["ok"])

    def test_no_receipt_files(self):
        for name in ("claim.prml.tsr", "claim.prml.rekor.json"):
            os.remove(Path(self.tmp) / name)
        r = run("receipt", "verify", "claim.prml.yaml", cwd=self.tmp)
        self.assertEqual(r.returncode, 2)


class _MockRegistry(http.server.BaseHTTPRequestHandler):
    answer_hash = HASH

    def log_message(self, *a):
        pass

    def do_POST(self):
        n = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(n))
        assert "yaml" in body
        resp = {"hash": self.answer_hash, "permalink": f"http://127.0.0.1/{self.answer_hash}",
                "timestamp": "2026-08-23T05:43:55Z", "existing": False,
                "tsa": {"gen_time": "2026-08-23T05:43:56Z", "token": f"/{HASH}.tsr"},
                "rekor": {"log_index": "76716892", "entry": f"/{HASH}.rekor"}}
        out = json.dumps(resp).encode()
        self.send_response(201)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(out)))
        self.end_headers()
        self.wfile.write(out)

    def do_GET(self):
        files = {f"/{HASH}.tsr": FIX / "claim.prml.tsr", f"/{HASH}.rekor": FIX / "claim.prml.rekor.json"}
        f = files.get(self.path)
        if not f:
            self.send_response(404)
            self.end_headers()
            return
        data = f.read_bytes()
        self.send_response(200)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


class Anchor(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        shutil.copy(FIX / "claim.prml.yaml", self.tmp)
        self.srv = http.server.HTTPServer(("127.0.0.1", 0), _MockRegistry)
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()
        self.url = f"http://127.0.0.1:{self.srv.server_address[1]}"

    def tearDown(self):
        self.srv.shutdown()
        self.srv.server_close()
        _MockRegistry.answer_hash = HASH
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_anchor_saves_receipt(self):
        r = run("anchor", "claim.prml.yaml", "--registry", self.url, cwd=self.tmp)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        for name in ("claim.prml.receipt.json", "claim.prml.tsr", "claim.prml.rekor.json"):
            self.assertTrue((Path(self.tmp) / name).exists(), name)
        if HAVE_EXTRA:
            v = run("receipt", "verify", "claim.prml.yaml", cwd=self.tmp)
            self.assertEqual(v.returncode, 0, v.stdout + v.stderr)

    def test_anchor_refuses_a_different_hash(self):
        _MockRegistry.answer_hash = "0" * 64
        r = run("anchor", "claim.prml.yaml", "--registry", self.url, cwd=self.tmp)
        self.assertEqual(r.returncode, 2)
        self.assertIn("differs from the local canonical hash", r.stderr)
        self.assertFalse((Path(self.tmp) / "claim.prml.receipt.json").exists())

    def test_plain_http_rejected_for_remote_hosts(self):
        r = run("anchor", "claim.prml.yaml", "--registry", "http://registry.example", cwd=self.tmp)
        self.assertEqual(r.returncode, 2)


if __name__ == "__main__":
    unittest.main()
