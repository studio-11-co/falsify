"""Registry receipts for PRML manifests: anchor and verify offline.

`falsify anchor <spec>` posts a manifest to a PRML registry (default
registry.falsify.dev), checks that the registry hashed the same canonical
bytes, and saves the receipt next to the manifest:

    <stem>.prml.receipt.json   the registry's JSON answer (accuracy.prml.yaml -> accuracy.prml.receipt.json)
    <stem>.prml.tsr            RFC 3161 TimeStampResp over the manifest hash
    <stem>.prml.rekor.json     the Rekor v2 transparency-log entry

`falsify receipt verify <spec>` checks those files against the manifest without
trusting the registry and without OpenSSL:

    * RFC 3161: the token's messageImprint equals the manifest hash, its
      signature verifies, and the TSA certificate chains to the pinned
      Sigstore TSA root (or to roots from --trusted-root).
    * Rekor: the hashedrekord digest equals the manifest hash, the RFC 9162
      inclusion proof reaches the checkpoint root, and the checkpoint is
      signed by the pinned log key (or a key from --trusted-root).

What a verified receipt shows: the manifest bytes existed no later than the
TSA time and the log integration time. It does not show that the run happened
after that time, or that any reported result is true.

Verification needs the optional extra: pip install "falsify[receipt]"
(rfc3161-client and cryptography). Anchoring needs only the standard library.
"""

from __future__ import annotations

import base64
import hashlib
import json
import re
import urllib.error
import urllib.request
from typing import Any

DEFAULT_REGISTRY = "https://registry.falsify.dev"

# Pinned trust anchors, copied from Sigstore's public-good trusted_root.json
# (TUF target, sha256 6494e21ea73fa7ee769f85f57d5a3e6a08725eae1e38c755fc3517c9e6bc0b66,
# read 28 Oct 2026). Override with --trusted-root <trusted_root.json>.
#
# Timestamp authority root "sigstore-tsa-selfsigned" (valid 2025-04-08 to 2035-04-06),
# SHA-256 fingerprint 2aca8fea5d3ce48b01cc77076293c280e6c23ffe44034757ee7833ca9f45d633.
SIGSTORE_TSA_ROOT_PEM = """-----BEGIN CERTIFICATE-----
MIIB9zCCAXygAwIBAgIUV7f0GLDOoEzIh8LXSW80OJiUp14wCgYIKoZIzj0EAwMw
OTEVMBMGA1UEChMMc2lnc3RvcmUuZGV2MSAwHgYDVQQDExdzaWdzdG9yZS10c2Et
c2VsZnNpZ25lZDAeFw0yNTA0MDgwNjU5NDNaFw0zNTA0MDYwNjU5NDNaMDkxFTAT
BgNVBAoTDHNpZ3N0b3JlLmRldjEgMB4GA1UEAxMXc2lnc3RvcmUtdHNhLXNlbGZz
aWduZWQwdjAQBgcqhkjOPQIBBgUrgQQAIgNiAAQUQNtfRT/ou3YATa6wB/kKTe70
cfJwyRIBovMnt8RcJph/COE82uyS6FmppLLL1VBPGcPfpQPYJNXzWwi8icwhKQ6W
/Qe2h3oebBb2FHpwNJDqo+TMaC/tdfkv/ElJB72jRTBDMA4GA1UdDwEB/wQEAwIB
BjASBgNVHRMBAf8ECDAGAQH/AgEAMB0GA1UdDgQWBBSY7AHvf7tR/9SVHm+KiJhT
B4nOvzAKBggqhkjOPQQDAwNpADBmAjEAwGEGrfGZR1cen1R8/DTVMI943LssZmJR
tDp/i7SfGHmGRP6gRbuj9vOK3b67Z0QQAjEAuT2H673LQEaHTcyQSZrkp4mX7Wwk
mF+sVbkYY5mXN+RMH13KUEHHOqASaemYWK/E
-----END CERTIFICATE-----
"""

# Rekor v2 log keys by checkpoint origin (Ed25519, raw 32-byte key, base64).
REKOR_LOG_KEYS = {
    "log2025-1.rekor.sigstore.dev": "t8rlp1knGwjfbcXAYPYAkn0XiLz1x8O4t0YkEhie244=",
}


class ReceiptError(Exception):
    """Raised when a receipt cannot be fetched or parsed."""


def receipt_paths(spec_path: str) -> dict[str, str]:
    # accuracy.prml.yaml -> accuracy.prml.tsr (not accuracy.prml.prml.tsr)
    stem = re.sub(r"(\.prml)?\.(ya?ml|json)$", "", spec_path)
    if stem == spec_path:
        stem = re.sub(r"\.[^.]+$", "", spec_path)
    return {
        "receipt": stem + ".prml.receipt.json",
        "tsr": stem + ".prml.tsr",
        "rekor": stem + ".prml.rekor.json",
    }


def _ua() -> str:
    try:
        from falsify_prml import __version__
    except Exception:  # pragma: no cover
        __version__ = "?"
    return f"falsify/{__version__} (+https://falsify.dev)"


def _check_registry_url(url: str) -> str:
    url = url.rstrip("/")
    if url.startswith("https://"):
        return url
    if re.match(r"^http://(127\.0\.0\.1|localhost)(:\d+)?$", url):
        return url  # local test registries only
    raise ReceiptError(f"registry URL must start with https:// (got {url!r})")


def _http(url: str, data: bytes | None = None, timeout: float = 20.0) -> bytes:
    headers = {"User-Agent": _ua()}
    if data is not None:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method="POST" if data is not None else "GET")
    try:
        # Scheme is checked by _check_registry_url (https, or http only to localhost).
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # nosec B310
            return resp.read()
    except urllib.error.HTTPError as e:
        body = e.read()[:300].decode("utf-8", "replace")
        raise ReceiptError(f"{url}: HTTP {e.code} {body}") from e
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        raise ReceiptError(f"{url}: {e}") from e


def anchor(spec_path: str, expected_hash: str, registry: str = DEFAULT_REGISTRY,
           handle: str | None = None, sealed: bool = False) -> dict[str, Any]:
    """POST the manifest text to <registry>/commit and save the receipt files.

    Raises ReceiptError if the registry is unreachable, answers with an error,
    or returns a hash other than ``expected_hash`` (the local canonical hash).
    """
    registry = _check_registry_url(registry)
    with open(spec_path, "r", encoding="utf-8") as fh:
        text = fh.read()
    payload: dict[str, Any] = {"yaml": text}
    if handle:
        payload["handle"] = handle
    if sealed:
        payload["sealed"] = True
    raw = _http(f"{registry}/commit", json.dumps(payload).encode("utf-8"))
    try:
        resp = json.loads(raw)
    except json.JSONDecodeError as e:
        raise ReceiptError(f"registry answered non-JSON: {raw[:200]!r}") from e
    got = resp.get("hash")
    if got != expected_hash:
        raise ReceiptError(
            f"registry hash {got!r} differs from the local canonical hash {expected_hash}; "
            "nothing was saved"
        )
    paths = receipt_paths(spec_path)
    with open(paths["receipt"], "w", encoding="utf-8") as fh:
        json.dump(resp, fh, indent=2, sort_keys=True)
        fh.write("\n")
    saved = {"receipt": paths["receipt"]}
    for key, field, ext in (("tsr", "tsa", ".tsr"), ("rekor", "rekor", ".rekor")):
        if resp.get(field):
            try:
                blob = _http(f"{registry}/{got}{ext}")
            except ReceiptError:
                continue  # anchors are best-effort on the registry side too
            with open(paths[key], "wb") as fh:
                fh.write(blob)
            saved[key] = paths[key]
    resp["_saved"] = saved
    return resp


def fetch_receipt(spec_path: str, digest_hex: str, registry: str = DEFAULT_REGISTRY) -> dict[str, str]:
    """GET the TSA token and Rekor entry for ``digest_hex`` and save them."""
    registry = _check_registry_url(registry)
    paths = receipt_paths(spec_path)
    saved = {}
    for key, ext in (("tsr", ".tsr"), ("rekor", ".rekor")):
        try:
            blob = _http(f"{registry}/{digest_hex}{ext}")
        except ReceiptError:
            continue
        with open(paths[key], "wb") as fh:
            fh.write(blob)
        saved[key] = paths[key]
    return saved


# ── verification ──────────────────────────────────────────────────────────

def load_trust(trusted_root_path: str | None = None) -> dict[str, Any]:
    """Return {"tsa_roots": [PEM bytes...], "intermediates": [...], "log_keys": {origin: raw32}}."""
    if not trusted_root_path:
        return {
            "tsa_roots": [SIGSTORE_TSA_ROOT_PEM.encode()],
            "intermediates": [],
            "log_keys": {k: base64.b64decode(v) for k, v in REKOR_LOG_KEYS.items()},
        }
    from cryptography import x509
    from cryptography.hazmat.primitives import serialization
    with open(trusted_root_path, "r", encoding="utf-8") as fh:
        tr = json.load(fh)
    roots, inters = [], []
    for ta in tr.get("timestampAuthorities", []):
        der = [base64.b64decode(c["rawBytes"]) for c in ta["certChain"]["certificates"]]
        certs = [x509.load_der_x509_certificate(d) for d in der]
        roots.append(certs[-1].public_bytes(serialization.Encoding.PEM))
        inters.extend(c.public_bytes(serialization.Encoding.PEM) for c in certs[1:-1])
    keys = {}
    for tl in tr.get("tlogs", []):
        pk = tl.get("publicKey", {})
        if pk.get("keyDetails") != "PKIX_ED25519":
            continue
        origin = re.sub(r"^https?://", "", tl.get("baseUrl", "")).rstrip("/")
        pub = serialization.load_der_public_key(base64.b64decode(pk["rawBytes"]))
        keys[origin] = pub.public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    return {"tsa_roots": roots, "intermediates": inters, "log_keys": keys}


def verify_tsr(tsr: bytes, digest_hex: str, trust: dict[str, Any]) -> dict[str, Any]:
    """Verify an RFC 3161 TimeStampResp over ``digest_hex``."""
    from cryptography import x509
    from rfc3161_client import VerifierBuilder, decode_timestamp_response

    out: dict[str, Any] = {"ok": False, "gen_time": None, "imprint_match": False, "error": None}
    try:
        resp = decode_timestamp_response(tsr)
    except Exception as e:
        out["error"] = f"cannot parse token: {e}"
        return out
    info = resp.tst_info
    out["gen_time"] = info.gen_time.isoformat()
    imprint = info.message_imprint.message.hex()
    out["imprint_match"] = imprint == digest_hex
    if not out["imprint_match"]:
        out["error"] = f"token timestamps {imprint}, not the manifest hash"
        return out
    errors = []
    for root_pem in trust["tsa_roots"]:
        try:
            builder = VerifierBuilder(
                roots=[x509.load_pem_x509_certificate(root_pem)],
                intermediates=[x509.load_pem_x509_certificate(p) for p in trust["intermediates"]],
            )
            builder.build().verify(resp, bytes.fromhex(digest_hex))
            out["ok"] = True
            out["error"] = None
            return out
        except Exception as e:  # try the next root
            msg = str(e) or type(e).__name__
            errors.append(msg.split(": ErrorStack")[0][:160])
    out["error"] = "signature or certificate chain did not verify: " + "; ".join(errors)
    return out


def _inclusion_ok(index: int, size: int, leaf: bytes, proof: list[bytes], root: bytes) -> bool:
    """RFC 9162 section 2.1.3.2 inclusion proof check."""
    if index >= size:
        return False
    fn, sn, r = index, size - 1, leaf
    for p in proof:
        if sn == 0:
            return False
        if fn & 1 or fn == sn:
            r = hashlib.sha256(b"\x01" + p + r).digest()
            if not fn & 1:
                while True:
                    fn >>= 1
                    sn >>= 1
                    if fn & 1 or fn == 0:
                        break
        else:
            r = hashlib.sha256(b"\x01" + r + p).digest()
        fn >>= 1
        sn >>= 1
    return sn == 0 and r == root


def verify_rekor(entry_json: bytes, digest_hex: str, trust: dict[str, Any]) -> dict[str, Any]:
    """Verify a Rekor v2 hashedrekord entry with inclusion proof and signed checkpoint."""
    out: dict[str, Any] = {"ok": False, "log_index": None, "origin": None, "digest_match": False,
                           "inclusion_ok": False, "checkpoint_signed": None, "error": None}
    try:
        doc = json.loads(entry_json)
        entry = doc.get("entry", doc)
        body = base64.b64decode(entry["canonicalizedBody"])
        spec = json.loads(body)["spec"]
        data = (spec.get("hashedRekordV002") or spec.get("hashedRekordV001") or {}).get("data", {})
        digest = base64.b64decode(data["digest"]).hex()
        ip = entry["inclusionProof"]
        index, size = int(ip["logIndex"]), int(ip["treeSize"])
        root = base64.b64decode(ip["rootHash"])
        proof = [base64.b64decode(h) for h in ip.get("hashes", [])]
        envelope = ip["checkpoint"]["envelope"]
    except (KeyError, ValueError, TypeError) as e:
        out["error"] = f"cannot parse Rekor entry: {e}"
        return out
    out["log_index"] = index
    out["digest_match"] = digest == digest_hex
    if not out["digest_match"]:
        out["error"] = f"log entry covers {digest}, not the manifest hash"
        return out
    leaf = hashlib.sha256(b"\x00" + body).digest()
    out["inclusion_ok"] = _inclusion_ok(index, size, leaf, proof, root)
    if not out["inclusion_ok"]:
        out["error"] = "inclusion proof does not reach the root hash"
        return out
    text, _, sig_lines = envelope.partition("\n\n")
    lines = text.split("\n")
    out["origin"] = origin = lines[0]
    if len(lines) < 3 or lines[1] != str(size) or base64.b64decode(lines[2]) != root:
        out["error"] = "checkpoint does not match the proof (size or root hash)"
        return out
    key = trust["log_keys"].get(origin)
    if key is None:
        out["checkpoint_signed"] = None
        out["error"] = f"no pinned key for log {origin}; inclusion checked, checkpoint signature not checked"
        return out
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
    pub = Ed25519PublicKey.from_public_bytes(key)
    key_hash = hashlib.sha256(origin.encode() + b"\n\x01" + key).digest()[:4]
    signed = False
    for line in sig_lines.strip().split("\n"):
        parts = line.split(" ")
        if len(parts) != 3 or parts[1] != origin:
            continue
        blob = base64.b64decode(parts[2])
        if blob[:4] != key_hash:
            continue
        try:
            pub.verify(blob[4:], (text + "\n").encode())
            signed = True
            break
        except Exception:
            continue
    out["checkpoint_signed"] = signed
    if not signed:
        out["error"] = "checkpoint signature did not verify with the log key"
        return out
    out["ok"] = True
    return out
