"""Static checks for docs/CASE_STUDIES.md."""

from __future__ import annotations

import re
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CASE_STUDIES = REPO_ROOT / "docs" / "CASE_STUDIES.md"
README = REPO_ROOT / "README.md"
SUBMISSION = REPO_ROOT / "SUBMISSION.md"

EMOJI_RE = re.compile(
    "["
    "\U0001F300-\U0001FAFF"
    "\U00002600-\U000027BF"
    "\U0001F000-\U0001F2FF"
    "]"
)


def _section(text: str, heading: str) -> str:
    """Return the body of a `### heading` section up to the next `### ` / EOF."""
    start = text.find(heading)
    if start == -1:
        return ""
    after = start + len(heading)
    nxt = text.find("\n### ", after)
    return text[after:nxt] if nxt != -1 else text[after:]


class CaseStudiesDocTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        cls.text = CASE_STUDIES.read_text()

    def test_file_exists(self) -> None:
        self.assertTrue(
            CASE_STUDIES.is_file(),
            f"missing {CASE_STUDIES}",
        )

    def test_has_three_cases(self) -> None:
        for heading in ("### Case 1", "### Case 2", "### Case 3"):
            self.assertIn(
                heading, self.text,
                f"doc missing heading {heading!r}",
            )

    def test_case_1_mentions_ndcg_or_ml_team(self) -> None:
        body = _section(self.text, "### Case 1")
        self.assertTrue(
            "NDCG" in body or "ML team" in body,
            "Case 1 should mention NDCG or ML team context",
        )

    def test_case_2_mentions_latency(self) -> None:
        body = _section(self.text, "### Case 2")
        self.assertIn(
            "latency", body.lower(),
            "Case 2 should mention latency in its body",
        )

    def test_case_3_mentions_pre_registration(self) -> None:
        body = _section(self.text, "### Case 3")
        self.assertIn(
            "pre-registration", body.lower(),
            "Case 3 should mention pre-registration",
        )

    def test_has_shared_patterns_section(self) -> None:
        self.assertIn(
            "### Shared patterns", self.text,
            "doc missing `### Shared patterns` section",
        )

    def test_has_further_reading_section(self) -> None:
        self.assertIn(
            "### Further reading", self.text,
            "doc missing `### Further reading` section",
        )

    def test_no_emoji(self) -> None:
        match = EMOJI_RE.search(self.text)
        self.assertIsNone(
            match,
            f"doc contains emoji at offset "
            f"{match.start() if match else -1}",
        )

    def test_no_nested_code_fences(self) -> None:
        fence_count = sum(
            1 for line in self.text.splitlines()
            if line.strip().startswith("```")
        )
        self.assertEqual(
            fence_count % 2, 0,
            f"uneven code-fence count: {fence_count}",
        )

    def test_readme_links_case_studies(self) -> None:
        self.assertIn(
            "docs/CASE_STUDIES.md", README.read_text(),
            "README.md does not link to docs/CASE_STUDIES.md",
        )

    def test_submission_links_case_studies(self) -> None:
        self.assertIn(
            "docs/CASE_STUDIES.md", SUBMISSION.read_text(),
            "SUBMISSION.md does not link to docs/CASE_STUDIES.md",
        )

    def test_every_case_shows_falsify_command(self) -> None:
        for heading in ("### Case 1", "### Case 2", "### Case 3"):
            body = _section(self.text, heading)
            self.assertRegex(
                body, r"(?m)^(?:    |\t)falsify(?:-engine)? ",
                f"{heading} has no indented `falsify ` command",
            )


if __name__ == "__main__":
    unittest.main()
