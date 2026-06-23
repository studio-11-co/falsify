"""Tests for TUTORIAL.md."""

from __future__ import annotations

import re
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
TUTORIAL = REPO_ROOT / "TUTORIAL.md"
README = REPO_ROOT / "README.md"
CONTRIBUTING = REPO_ROOT / "CONTRIBUTING.md"
CHANGELOG = REPO_ROOT / "CHANGELOG.md"


class TutorialTests(unittest.TestCase):
    def setUp(self) -> None:
        self.assertTrue(TUTORIAL.exists(), f"TUTORIAL.md missing at {TUTORIAL}")
        self.text = TUTORIAL.read_text()

    def test_tutorial_exists(self) -> None:
        self.assertTrue(TUTORIAL.is_file())
        self.assertGreater(len(self.text), 0)

    def test_has_all_sections(self) -> None:
        # TUTORIAL.md teaches the core PRML path in six steps
        # (lock -> verify PASS -> FAIL -> TAMPERED).
        for n in range(1, 7):
            self.assertRegex(
                self.text,
                rf"(?m)^## Step {n}\b",
                f"missing '## Step {n}' heading",
            )
        for heading in (
            "What you will build",
            "Install",
            "What just happened",
            "Where to go next",
        ):
            self.assertIn(heading, self.text, f"missing section: {heading!r}")

    def test_mentions_core_commands(self) -> None:
        # The PRML manifest path — these are the commands a reader copy-pastes.
        for cmd in (
            "falsify init",
            "falsify lock",
            "falsify verify",
        ):
            self.assertIn(cmd, self.text, f"missing command: {cmd!r}")
        # The three verdicts the tutorial must demonstrate.
        for verdict in ("PASS", "FAIL", "TAMPERED"):
            self.assertIn(verdict, self.text, f"missing verdict: {verdict!r}")

    def test_engine_tutorial_uses_engine_binary(self) -> None:
        # The workflow-engine walkthrough lives in its own doc and must drive
        # the `falsify-engine` binary, not the PRML `falsify` CLI.
        engine = REPO_ROOT / "docs" / "ENGINE-TUTORIAL.md"
        self.assertTrue(engine.is_file(), f"ENGINE-TUTORIAL.md missing at {engine}")
        etext = engine.read_text()
        self.assertIn("falsify-engine run", etext)
        self.assertNotRegex(
            etext, r"(?m)^    falsify (run|verdict|lock|init) ",
            "engine tutorial must use the `falsify-engine` binary for engine commands",
        )

    def test_no_nested_code_fences(self) -> None:
        self.assertEqual(
            self.text.count("```"),
            0,
            "TUTORIAL.md must use 4-space indented code blocks, "
            "not triple-backtick fences",
        )

    def test_readme_links_tutorial(self) -> None:
        self.assertIn("(TUTORIAL.md)", README.read_text())

    def test_contributing_mentions_tutorial(self) -> None:
        self.assertIn("TUTORIAL.md", CONTRIBUTING.read_text())

    def test_changelog_mentions_tutorial(self) -> None:
        # TUTORIAL.md must be referenced somewhere in CHANGELOG so its
        # role in the docs is documented. Originally scoped to the
        # [Unreleased] block, but releases now move content into
        # [X.Y.Z] sections and that's still a valid mention.
        text = CHANGELOG.read_text()
        self.assertIn("TUTORIAL", text)


if __name__ == "__main__":
    unittest.main()
