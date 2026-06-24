"""A fully deterministic, offline DeepEval metric — no LLM, no API key.

Exact-match accuracy: the model output must equal the expected output after
light normalization (lowercase, strip, collapse whitespace). One metric
instance scores a single LLMTestCase (1.0 or 0.0); the harness averages over
the set to obtain the dataset-level accuracy claim that PRML locks.

This is intentionally LLM-free so the example runs identically on any machine
with no credentials — the same property a PRML conformance check needs.
"""
from __future__ import annotations

import re

from deepeval.metrics import BaseMetric
from deepeval.test_case import LLMTestCase


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


class ExactMatchMetric(BaseMetric):
    """Deterministic exact-match metric (DeepEval BaseMetric subclass)."""

    def __init__(self, threshold: float = 0.5):
        self.threshold = threshold

    def measure(self, test_case: LLMTestCase) -> float:
        self.score = (
            1.0
            if _normalize(test_case.actual_output)
            == _normalize(test_case.expected_output)
            else 0.0
        )
        self.success = self.score >= self.threshold
        return self.score

    async def a_measure(self, test_case: LLMTestCase) -> float:
        return self.measure(test_case)

    def is_successful(self) -> bool:
        return self.success

    @property
    def __name__(self):
        return "Exact Match"
