#!/usr/bin/env python3
"""Tiny, real accuracy eval. Reads eval_set.jsonl, prints the observed accuracy.

    python3 run_eval.py            # -> 0.9

Pass that value to `falsify verify accuracy.prml.yaml --observed <value>`.
No network, no API keys — fully reproducible, so the manifest is too.
"""
import json
from pathlib import Path

rows = [json.loads(l) for l in Path(__file__).with_name("eval_set.jsonl").read_text().splitlines() if l.strip()]
correct = sum(1 for r in rows if r["prediction"] == r["gold"])
acc = correct / len(rows)
print(f"{acc:.4f}")
