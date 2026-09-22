#!/usr/bin/env bash
# Re-verify the PREP-Eval worked example offline. No network, no account.
set -euo pipefail
cd "$(dirname "$0")"
PY="${PYTHON:-python3}"
CLI=../../falsify_prml.py
LNK=../../falsify.py

H1=$(cut -c1-64 preregistration-v1.prml.prml.sha256)
H2=$(cut -c1-64 preregistration-v2.prml.prml.sha256)

echo "1/4  manifest v1 hash"
$PY "$CLI" verify preregistration-v1.prml.yaml --expected-hash "$H1"
echo "2/4  manifest v2 hash + dataset bytes + predicate (observed 0.88)"
$PY "$CLI" verify preregistration-v2.prml.yaml --expected-hash "$H2" --dataset cphos-en-sample-v2.jsonl --observed 0.88
echo "3/4  v1 dataset bytes"
$PY - <<'EOF'
import hashlib, re, sys
want = re.search(r"hash:\s*([0-9a-f]{64})", open("preregistration-v1.prml.yaml").read()).group(1)
got = hashlib.sha256(open("cphos-en-sample.jsonl", "rb").read()).hexdigest()
print(("OK  " if got == want else "FAIL") + "  v1 dataset sha256 " + got)
sys.exit(0 if got == want else 11)
EOF
echo "4/4  linkage chain final -> start -> manifest"
$PY "$LNK" linkage verify linkage-final.yaml --start linkage-start.yaml --manifest preregistration-v2.prml.yaml
echo
echo "PREP-Eval example: all checks passed"
