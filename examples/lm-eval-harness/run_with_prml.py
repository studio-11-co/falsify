"""Runnable, offline lm-evaluation-harness + PRML demo — no model download,
no API key, no network.

Two scenarios, both driving the real harness (``lm_eval.simple_evaluate``) over
a local 10-question task with a scripted model:

  A. Honest PASS  — lock exact_match >= 0.85, run, observe 0.90, verify -> PASS.
  B. Gamed run    — lock exact_match >= 0.95, run, observe 0.90 (a FAIL); then
                    quietly lower the locked threshold to 0.85 to make it green
                    -> PRML returns TAMPERED, not PASS.

Run:  python run_with_prml.py
"""
from __future__ import annotations

import copy
import os
import sys

import lm_eval
from lm_eval.api.model import LM
from lm_eval.tasks import TaskManager

from prml_lm_eval import PrmlLock, lock_harness_claim, verify_observed

HERE = os.path.dirname(os.path.abspath(__file__))
os.chdir(HERE)  # the task YAML's data_files path is relative to the example root
TASK_DIR = os.path.join(HERE, "toy_task")
TASK_YAML = os.path.join(TASK_DIR, "prml_toy_qa.yaml")
DATASET = os.path.join(TASK_DIR, "toy_qa.jsonl")
SEED = 42
PRODUCER = "examples/lm-eval-harness (falsify)"

# The scripted model answers 9 of the 10 toy questions correctly and misses
# one on purpose, so exact_match lands at a deterministic 0.90.
ANSWERS = {
    "What is the capital of France?": "Paris",
    "What is 2 + 2?": "4",
    "What color is the clear daytime sky?": "blue",
    "How many days are in a week?": "7",
    "What is the chemical symbol for water?": "H2O",
    "What planet do humans live on?": "Earth",
    "What is the opposite of hot?": "cold",
    "How many legs does a spider have?": "8",
    "What is the first month of the year?": "January",
    "What gas do humans breathe in to survive?": "helium",  # deliberate miss
}


class ScriptedLM(LM):
    """A deterministic lm-eval model: canned answers, zero weights.

    Subclasses the harness's real ``LM`` interface, so the run below exercises
    the same task-loading, prompting, and metric pipeline a real model would.
    """

    def generate_until(self, requests):
        out = []
        for req in requests:
            context = req.args[0]
            question = context.split("Q: ", 1)[-1].split("\n", 1)[0].strip()
            out.append(ANSWERS.get(question, "unknown"))
        return out

    def loglikelihood(self, requests):  # pragma: no cover - unused output type
        raise NotImplementedError("scripted model only supports generate_until")

    def loglikelihood_rolling(self, requests):  # pragma: no cover - unused
        raise NotImplementedError("scripted model only supports generate_until")


def run_harness() -> float:
    """One real harness run over the toy task; returns observed exact_match."""
    results = lm_eval.simple_evaluate(
        model=ScriptedLM(),
        tasks=["prml_toy_qa"],
        task_manager=TaskManager(include_path=TASK_DIR),
        random_seed=SEED,
        numpy_random_seed=SEED,
        torch_random_seed=SEED,
        fewshot_random_seed=SEED,
    )
    metrics = results["results"]["prml_toy_qa"]
    key = next(k for k in metrics if k.startswith("exact_match"))
    return float(metrics[key])


def scenario_a() -> str:
    lock = lock_harness_claim(
        claim_id="01900000-0000-7000-8000-00001e4a0001",
        created_at="2026-07-30T12:00:00Z",
        task="prml_toy_qa",
        task_config_path=TASK_YAML,
        metric="exact_match",
        comparator=">=",
        threshold=0.85,
        dataset_id="examples/lm-eval-harness/toy_qa.jsonl",
        dataset_path=DATASET,
        seed=SEED,
        producer_id=PRODUCER,
    )
    print(f"[A] locked  exact_match >= 0.85   hash {lock.digest[:16]}…")
    observed = run_harness()
    print(f"[A] observed exact_match = {observed:.2f}")
    verdict = verify_observed(lock, observed)
    print(f"[A] verdict: {verdict}")
    return verdict


def scenario_b() -> str:
    lock = lock_harness_claim(
        claim_id="01900000-0000-7000-8000-00001e4a0002",
        created_at="2026-07-30T12:00:00Z",
        task="prml_toy_qa",
        task_config_path=TASK_YAML,
        metric="exact_match",
        comparator=">=",
        threshold=0.95,
        dataset_id="examples/lm-eval-harness/toy_qa.jsonl",
        dataset_path=DATASET,
        seed=SEED,
        producer_id=PRODUCER,
    )
    print(f"[B] locked  exact_match >= 0.95   hash {lock.digest[:16]}…")
    observed = run_harness()
    print(f"[B] observed exact_match = {observed:.2f}  (would FAIL the locked bar)")
    # The gamed move: quietly lower the threshold after seeing the result.
    softened = copy.deepcopy(lock.manifest)
    softened["threshold"] = 0.85
    verdict = verify_observed(lock, observed, current_manifest=softened)
    print(f"[B] verdict after softening the bar: {verdict}")
    return verdict


def main() -> int:
    a = scenario_a()
    print()
    b = scenario_b()
    ok = (a == "PASS") and (b == "TAMPERED")
    print()
    print("demo", "OK" if ok else "BROKEN", "— A must PASS, B must read TAMPERED")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
