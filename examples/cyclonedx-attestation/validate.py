#!/usr/bin/env python3
"""Validate bom.cdx.json against the CycloneDX 1.6 JSON schema, then check
that the PRML evidence inside it is internally consistent.

Two independent checks, on purpose:

  1. Schema: the BOM is a well-formed CycloneDX 1.6 document (declarations,
     claims, evidence, affirmation).  Any CycloneDX-aware tool can do this
     part; we use jsonschema so the example has no CycloneDX dependency.
  2. PRML: the canonical hash recorded as evidence equals the hash of the
     manifest shipped next to it, and the observed value really satisfies the
     pre-registered comparator/threshold.  This is the part the BOM consumer
     can redo offline without trusting the BOM author.

Usage:  python3 validate.py            (needs: pip install jsonschema pyyaml)
Exit 0 = both checks pass.
"""
import hashlib
import json
import os
import subprocess
import sys
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, ".schema-cache")
SCHEMA_BASE = "https://raw.githubusercontent.com/CycloneDX/specification/master/schema/"
SCHEMAS = ["bom-1.6.schema.json", "spdx.schema.json", "jsf-0.82.schema.json"]


def fetch(name):
    os.makedirs(CACHE, exist_ok=True)
    path = os.path.join(CACHE, name)
    if not os.path.exists(path):
        urllib.request.urlretrieve(SCHEMA_BASE + name, path)
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def check_schema(bom):
    import jsonschema
    from jsonschema import Draft7Validator
    from referencing import Registry, Resource

    main = fetch(SCHEMAS[0])
    resources = [(s, Resource.from_contents(fetch(s))) for s in SCHEMAS]
    registry = Registry().with_resources(resources)
    validator = Draft7Validator(main, registry=registry)
    errors = sorted(validator.iter_errors(bom), key=lambda e: list(e.path))
    for e in errors:
        print("schema:", "/".join(str(p) for p in e.path), "-", e.message[:160])
    return not errors


def prml_props(bom):
    """Collect prml:* properties from the BOM's metadata component.

    CycloneDX evidence entries carry no free-form properties, so the taxonomy
    values live on the component being attested (the same place a modelCard
    would sit); the evidence entries point at the artefacts by URL."""
    out = {}
    for p in bom.get("metadata", {}).get("component", {}).get("properties", []):
        if p["name"].startswith("prml:"):
            out[p["name"]] = p["value"]
    return out


def check_prml(bom):
    props = prml_props(bom)
    manifest = os.path.join(HERE, "manifest.prml.yaml")
    ok = True

    # Canonical hash: use the reference CLI if available, else fall back to
    # the sibling implementation in this repository.
    cli = [sys.executable, os.path.join(HERE, "..", "..", "falsify_prml.py")]
    try:
        h = subprocess.check_output(cli + ["hash", manifest], text=True).strip()
    except (OSError, subprocess.CalledProcessError):
        h = subprocess.check_output(["falsify", "hash", manifest], text=True).strip()
    want = props.get("prml:manifest:canonical-sha256")
    if h != want:
        print(f"prml: canonical hash mismatch\n  manifest: {h}\n  evidence: {want}")
        ok = False
    else:
        print(f"prml: canonical hash matches ({h[:16]}…)")

    # Predicate: observed value against the pre-registered bar.
    import yaml
    with open(manifest, encoding="utf-8") as f:
        m = yaml.safe_load(f)
    observed = float(props["prml:verify:observed"])
    thr = float(m["threshold"])
    cmp_ = m["comparator"]
    passed = {">=": observed >= thr, ">": observed > thr,
              "<=": observed <= thr, "<": observed < thr}[cmp_]
    verdict = "PASS" if passed else "FAIL"
    if verdict != props.get("prml:verify:verdict"):
        print(f"prml: verdict mismatch: computed {verdict}, evidence says {props.get('prml:verify:verdict')}")
        ok = False
    else:
        print(f"prml: verdict {verdict} ({m['metric']} {observed} {cmp_} {thr})")
    return ok


def main():
    with open(os.path.join(HERE, "bom.cdx.json"), encoding="utf-8") as f:
        bom = json.load(f)
    s = check_schema(bom)
    p = check_prml(bom)
    print("schema:", "OK" if s else "FAIL", "| prml:", "OK" if p else "FAIL")
    sys.exit(0 if (s and p) else 1)


if __name__ == "__main__":
    main()
