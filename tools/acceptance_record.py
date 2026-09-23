#!/usr/bin/env python3
"""Helpers for assembling an acceptance record (see examples/acceptance-record/).

  acceptance_record.py seal  NAME --role TEXT FILE...   write NAME.yaml listing the SHA-256 of FILE...
                                                       (the signed bytes), then commit it
  acceptance_record.py commit YAML [--name NAME]        commit a YAML record (PRML manifest, linkage
                                                       record or seal) to the registry
  acceptance_record.py bundle DIR -o OUT.zip            zip DIR for delivery, with a SHA256SUMS file

commit and seal save receipt-NAME.json and anchors/NAME.tsr next to the YAML. --dry-run prints
what would be sent and contacts nobody. Private keys (keys/demo-*, *.key, *.pem private) are
never put into a bundle.

The registry hash of a YAML record is the PRML canonical hash of its parsed content, not the
SHA-256 of the file bytes; VERIFY.sh recomputes it with falsify_prml.manifest_hash.
"""
import argparse, hashlib, json, os, sys, urllib.request, zipfile

REGISTRY = os.environ.get("FALSIFY_REGISTRY", "https://registry.falsify.dev")
NEVER_BUNDLE = ("keys/demo-supplier", "keys/demo-client", "keys/demo-falsify")


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def post_yaml(path):
    req = urllib.request.Request(REGISTRY + "/commit", data=open(path, "rb").read(),
                                 headers={"content-type": "text/yaml"}, method="POST")
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def fetch(url, out):
    with urllib.request.urlopen(url, timeout=60) as r, open(out, "wb") as f:
        f.write(r.read())


def commit(path, name, dry_run):
    base = os.path.dirname(os.path.abspath(path))
    if dry_run:
        print(f"[dry-run] would POST {path} to {REGISTRY}/commit and save receipt-{name}.json, anchors/{name}.tsr")
        return None
    rec = post_yaml(path)
    json.dump(rec, open(os.path.join(base, f"receipt-{name}.json"), "w"))
    os.makedirs(os.path.join(base, "anchors"), exist_ok=True)
    fetch(f"{REGISTRY}/{rec['hash']}.tsr", os.path.join(base, "anchors", f"{name}.tsr"))
    print(f"{name}: {rec['kind']} {rec['hash']} at {rec['timestamp']}  {rec['permalink']}")
    return rec


def cmd_seal(a):
    lines = ["record: acceptance-record-seal/0", f"role: {json.dumps(a.role)}", "documents:"]
    for f in a.files:
        lines.append(f"  {json.dumps(f)}: {sha256(f)}")
    out = a.name + ".yaml"
    text = "\n".join(lines) + "\n"
    if os.path.exists(out) and open(out).read() != text:
        sys.exit(f"{out} exists with different content; refusing to overwrite a seal record")
    open(out, "w").write(text)
    print(text, end="")
    commit(out, a.name, a.dry_run)


def cmd_commit(a):
    name = a.name or os.path.basename(a.yaml).replace(".prml.yaml", "").replace(".yaml", "")
    commit(a.yaml, name, a.dry_run)


def cmd_bundle(a):
    root = os.path.abspath(a.dir)
    files = []
    for dp, dn, fn in os.walk(root):
        dn[:] = [d for d in dn if d not in (".git", "__pycache__")]
        for f in sorted(fn):
            rel = os.path.relpath(os.path.join(dp, f), root)
            if rel in NEVER_BUNDLE or rel.endswith((".key",)) or f == ".gitignore":
                continue
            files.append(rel)
    files.sort()
    sums = "".join(f"{sha256(os.path.join(root, r))}  {r}\n" for r in files)
    with zipfile.ZipFile(a.out, "w", zipfile.ZIP_DEFLATED) as z:
        for r in files:
            z.write(os.path.join(root, r), r)
        z.writestr("SHA256SUMS", sums)
    print(f"{a.out}: {len(files)} files + SHA256SUMS, sha256 {sha256(a.out)}")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("seal"); s.add_argument("name"); s.add_argument("--role", required=True)
    s.add_argument("files", nargs="+"); s.add_argument("--dry-run", action="store_true"); s.set_defaults(fn=cmd_seal)
    c = sub.add_parser("commit"); c.add_argument("yaml"); c.add_argument("--name")
    c.add_argument("--dry-run", action="store_true"); c.set_defaults(fn=cmd_commit)
    b = sub.add_parser("bundle"); b.add_argument("dir"); b.add_argument("-o", "--out", required=True); b.set_defaults(fn=cmd_bundle)
    a = p.parse_args(); a.fn(a)


if __name__ == "__main__":
    main()
