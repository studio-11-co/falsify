#!/usr/bin/env python3
"""Export test-vectors.json into the RFC v0.2 P-04 directory format.

Writes vectors/<vector_id>/manifest.yaml (canonical bytes) and
vectors/<vector_id>/expected_hash.txt for every vector. The directory
tree is committed; implementers can consume it without running this
script. Re-run after editing test-vectors.json.
"""

from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).parent
OUT = HERE / "vectors"


def main() -> int:
    vectors = json.loads((HERE / "test-vectors.json").read_text(encoding="utf-8"))
    OUT.mkdir(exist_ok=True)
    written = 0
    for v in vectors:
        d = OUT / v["id"]
        d.mkdir(exist_ok=True)
        # canonical bytes ARE the manifest.yaml content — byte-precision matters
        (d / "manifest.yaml").write_text(v["canonical"], encoding="utf-8")
        (d / "expected_hash.txt").write_text(v["hash"] + "\n", encoding="utf-8")
        written += 1
    print(f"wrote {written} vector directories under {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
