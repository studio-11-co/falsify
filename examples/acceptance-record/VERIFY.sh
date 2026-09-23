#!/usr/bin/env bash
# Re-verify the illustrative acceptance record offline. No network, no account, no trust in us.
# Needs: python3 with pyyaml, OpenSSL 3 (macOS LibreSSL cannot verify these RFC 3161 tokens), ssh-keygen (OpenSSH 8+).
set -euo pipefail
cd "$(dirname "$0")"
PY="${PYTHON:-python3}"
OSSL="${OPENSSL:-openssl}"
if ! "$OSSL" version | grep -q '^OpenSSL 3'; then
  for c in /opt/homebrew/opt/openssl@3/bin/openssl /usr/local/opt/openssl@3/bin/openssl; do [ -x "$c" ] && OSSL="$c" && break; done
fi
CLI=../../falsify_prml.py
LNK=../../falsify.py
fail=0

echo "1/8  criteria records: hash, dataset bytes, verdict from result.json"
for c in C1 C2; do
  key=$([ "$c" = C1 ] && echo C1_impact_ratio || echo C2_accuracy)
  obs=$("$PY" -c "import json;print(json.load(open('result.json'))['$key'])")
  "$PY" "$CLI" verify "criteria-$c.prml.yaml" --expected-hash "$(cut -c1-64 criteria-$c.prml.prml.sha256)" --dataset german.data --observed "$obs" || fail=1
done

echo "2/8  linkage chains: final -> start -> criteria record"
for c in C1 C2; do
  "$PY" "$LNK" linkage verify "linkage-final-$c.yaml" --start "linkage-start-$c.yaml" --manifest "criteria-$c.prml.yaml" || fail=1
done

echo "3/8  signatures on the plan, report, conditions and statement (demo keys in keys/allowed_signers)"
for pair in "1-acceptance-plan.md client" "1-acceptance-plan.md supplier" "2-acceptance-report.md supplier" "2-acceptance-report.md client" "3-change-and-rereview.md client" "3-change-and-rereview.md supplier" "4-verification-statement.md falsify"; do
  set -- $pair
  [ -f "$1.$2.sig" ] || { echo "SKIP  $1.$2.sig not present"; continue; }
  ssh-keygen -Y verify -f keys/allowed_signers -I "demo-$2@acceptance-record.example" -n acceptance-record -s "$1.$2.sig" < "$1" || fail=1
done

echo "4/8  seal records list the exact bytes of each signed document"
"$PY" - <<'EOF' || fail=1
import hashlib, sys, yaml
bad = 0
for seal in ("seal-plan.yaml", "seal-report.yaml", "seal-statement.yaml"):
    try: s = yaml.safe_load(open(seal))
    except FileNotFoundError: print("SKIP  " + seal + " not present"); continue
    for name, want in s["documents"].items():
        got = hashlib.sha256(open(name, "rb").read()).hexdigest()
        ok = got == want; bad += not ok
        print(("OK  " if ok else "FAIL") + f"  {seal}: {name}")
    if "signers_file_sha256" in s:
        got = hashlib.sha256(open("keys/allowed_signers", "rb").read()).hexdigest()
        ok = got == s["signers_file_sha256"]; bad += not ok
        print(("OK  " if ok else "FAIL") + f"  {seal}: keys/allowed_signers")
sys.exit(1 if bad else 0)
EOF

echo "5/8  every registry record hash recomputes from the YAML on disk"
"$PY" - <<'EOF' || fail=1
import glob, json, sys
sys.path.insert(0, "../..")
import falsify_prml as fp
src = {"criteria-C1": "criteria-C1.prml.yaml", "criteria-C2": "criteria-C2.prml.yaml"}
bad = 0
for r in sorted(glob.glob("receipt-*.json")):
    n = r[len("receipt-"):-len(".json")]
    y = src.get(n, n + ".yaml")
    got = fp.manifest_hash(fp.load_manifest(y)); want = json.load(open(r))["hash"]
    ok = got == want; bad += not ok
    print(("OK  " if ok else "FAIL") + f"  {y} -> {want}")
sys.exit(1 if bad else 0)
EOF

echo "6/8  registry receipts carry a valid Ed25519 signature (key and message format in anchors/registry-pubkey.json)"
"$PY" - "$OSSL" <<'EOF' || fail=1
import base64, glob, json, os, subprocess, sys, tempfile
ossl = sys.argv[1]
k = json.load(open("anchors/registry-pubkey.json")); jwk = k["public_key_jwk"]
b64u = lambda s: base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))
der = bytes.fromhex("302a300506032b6570032100") + b64u(jwk["x"])
d = tempfile.mkdtemp(); pem = os.path.join(d, "pub.pem")
open(pem, "w").write("-----BEGIN PUBLIC KEY-----\n" + base64.b64encode(der).decode() + "\n-----END PUBLIC KEY-----\n")
bad = 0
for r in sorted(glob.glob("receipt-*.json")):
    j = json.load(open(r))
    open(os.path.join(d, "m"), "wb").write(f"falsify-receipt-v1\n{j['hash']}\n{j['timestamp']}".encode())
    open(os.path.join(d, "s"), "wb").write(b64u(j["signature"]["value"]))
    p = subprocess.run([ossl, "pkeyutl", "-verify", "-pubin", "-inkey", pem, "-rawin", "-in", os.path.join(d, "m"), "-sigfile", os.path.join(d, "s")], capture_output=True, text=True)
    ok = "Verified Successfully" in (p.stdout + p.stderr); bad += not ok
    print(("OK  " if ok else "FAIL") + f"  {r} (kid {j['signature']['kid']}, {j['timestamp']})")
sys.exit(1 if bad else 0)
EOF

echo "7/8  RFC 3161 timestamps verify against the time-stamping authority chain ($("$OSSL" version | cut -d' ' -f1-2))"
for r in receipt-*.json; do
  n=${r#receipt-}; n=${n%.json}
  h=$("$PY" -c "import json;print(json.load(open('$r'))['hash'])")
  t=$("$OSSL" ts -reply -in "anchors/$n.tsr" -text 2>/dev/null | sed -n 's/^Time stamp: //p')
  if "$OSSL" ts -verify -digest "$h" -in "anchors/$n.tsr" -CAfile anchors/tsa-chain.pem >/dev/null 2>&1; then
    echo "OK    $t  $n"
  else echo "FAIL  $n"; fail=1; fi
done

echo "8/8  order of the independent timestamps"
"$PY" - "$OSSL" <<'EOF' || fail=1
import subprocess, sys
from datetime import datetime
ossl = sys.argv[1]
def t(n):
    out = subprocess.run([ossl, "ts", "-reply", "-in", f"anchors/{n}.tsr", "-text"], capture_output=True, text=True).stdout
    line = [l for l in out.splitlines() if l.startswith("Time stamp:")][0].split(": ", 1)[1].replace(" GMT", "")
    return datetime.strptime(line, "%b %d %H:%M:%S %Y")
import os
seq = ["criteria-C1", "criteria-C2", "seal-plan", "linkage-start-C1", "linkage-start-C2", "linkage-final-C1", "linkage-final-C2", "seal-report"] + (["seal-statement"] if os.path.exists("anchors/seal-statement.tsr") else [])
ts = [t(n) for n in seq]
ok = all(a <= b for a, b in zip(ts, ts[1:]))
for n, x in zip(seq, ts): print(f"      {x:%H:%M:%S}  {n}")
print(("OK  " if ok else "FAIL") + "  criteria and signed plan anchored before the run-start records; report sealed after the run-final records")
sys.exit(0 if ok else 1)
EOF

echo
if [ "$fail" = 0 ]; then echo "Acceptance record AP-2026-001: all checks passed"; else echo "Acceptance record AP-2026-001: CHECKS FAILED"; exit 1; fi
echo "What this does not show: that the criteria are appropriate, that the results are correct, that the run"
echo "happened after the plan (the runner times are the supplier's statement), or that no other plan or run existed."
