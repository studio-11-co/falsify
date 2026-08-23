#!/usr/bin/env python3
"""Negative-conformance driver — every reference impl MUST reject these inputs.

Unlike the positive suites (which assert byte-identical canonical/hash output),
reject-vectors carry no canonical/hash: they are manifests that contain a
control / non-portable character (C0/C1, U+007F, U+2028/U+2029, U+FEFF) and so
MUST NOT lock. This driver feeds each vector's `input` to an implementation's
CLI (which takes a manifest path as its last argument) and asserts a NON-ZERO
exit — i.e. the impl rejected it rather than silently hashing a non-portable
manifest. A vector that the impl ACCEPTS (exit 0) is a parity regression.

Usage:
    check_reject.py -- <impl cmd ...>
        # the manifest path is appended as the final argument

Examples:
    check_reject.py -- python3 falsify.py lock
    check_reject.py -- node impl/js/falsify.js lock
    check_reject.py -- impl/go/falsify-go hash
    check_reject.py -- impl/rust/target/release/falsify-rs hash

Exit 0 iff every reject-vector was rejected by the impl.
"""
import argparse
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_VECTORS = os.path.join(HERE, "reject-vectors.json")


def main():
    ap = argparse.ArgumentParser(description="PRML negative-conformance driver")
    ap.add_argument("--vectors", default=DEFAULT_VECTORS,
                    help="reject-vectors.json (default: alongside this script)")
    ap.add_argument("--reads", default="json,yaml",
                    help="comma-separated manifest formats this impl ingests "
                         "(default: json,yaml). Vectors in a format the impl cannot "
                         "read are reported SKIP rather than counted as refusals — a "
                         "parser that chokes on the file proves nothing about the defect.")
    ap.add_argument("cmd", nargs=argparse.REMAINDER,
                    help="-- <impl cmd ...>  (manifest path appended last)")
    args = ap.parse_args()

    cmd = args.cmd
    if cmd and cmd[0] == "--":
        cmd = cmd[1:]
    if not cmd:
        ap.error("provide the implementation command after `--`")

    vectors = json.load(open(args.vectors, encoding="utf-8"))
    reads = {f.strip().lower() for f in args.reads.split(",") if f.strip()}
    leaked = 0
    skipped = 0
    tmpdir = tempfile.mkdtemp(prefix="prml-reject-")
    for v in vectors:
        if v.get("ext", "json").lower() not in reads:
            skipped += 1
            print(f"{'SKIP (not read)':20} {v['id']}  {v['title']}")
            continue
        # Some defects cannot survive a round-trip through a JSON object: a
        # duplicate key collapses to last-wins before the impl ever sees it, and
        # `.inf` has no JSON literal. Those vectors carry `raw` (verbatim manifest
        # text) plus `ext` instead of `input`.
        if "raw" in v:
            path = os.path.join(tmpdir, f"{v['id']}.{v.get('ext', 'yaml')}")
            with open(path, "w", encoding="utf-8") as f:
                f.write(v["raw"])
        else:
            path = os.path.join(tmpdir, f"{v['id']}.json")
            with open(path, "w", encoding="utf-8") as f:
                json.dump(v["input"], f, ensure_ascii=False)
        proc = subprocess.run(cmd + [path], capture_output=True, text=True)
        rejected = proc.returncode != 0
        # A non-zero exit alone does not prove the impl caught THIS defect: an impl
        # that cannot parse the file at all (a missing YAML library, say) rejects
        # every vector for a reason that has nothing to do with the vector. So the
        # diagnostic must also mention the reason the vector exists to provoke.
        output = (proc.stderr + proc.stdout).lower()
        # `expect` may be a list when conformant impls word the same refusal
        # differently (a YAML library's own duplicate-key error, say). Any one
        # phrasing matching is enough — the vector tests the refusal, not the prose.
        expect = v.get("expect", "")
        wanted = [expect] if isinstance(expect, str) else list(expect)
        on_point = any(w.lower() in output for w in wanted)
        if not rejected:
            status, bad = "FAIL (ACCEPTED!)", True
        elif not on_point:
            status, bad = "FAIL (WRONG REASON)", True
        else:
            status, bad = "PASS", False
        if bad:
            leaked += 1
        print(f"{status:20} {v['id']}  {v['title']}")
        if rejected and not on_point:
            first = (proc.stderr.strip() or proc.stdout.strip()).splitlines()
            print(f"{'':20}   expected {v.get('expect')!r}, got: "
                  f"{first[0][:90] if first else '(no output)'}")

    total = len(vectors)
    run = total - skipped
    print(f"\nResult: {run - leaked}/{run} reject-vectors correctly rejected"
          + (f" ({skipped} skipped: format not read by this impl)." if skipped else "."))
    sys.exit(10 if leaked else 0)


if __name__ == "__main__":
    main()
