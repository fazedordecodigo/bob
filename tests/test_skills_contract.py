"""Contract tests for issue #7 (skills package).

Seams (acceptance criteria of #7 / docs/SPEC.md — the public boundary):

1. Vendor attribution: skills/vendor/mattpocock/ ships LICENSE, NOTICE, and
   the upstream commit, plus the Pocock skills the spec names.
2. Agent Skills: skills/bob-check and skills/review-report expose name +
   description frontmatter.
3. CLI surface: bob-check quotes the SPEC command block and exit codes
   verbatim, so an agent invokes `bob check` as specified.
4. review-report: summarizes .bob/report.md into a Summary / Evidence / Merge Danger pull request body.
5. AGENTS.md: short index pointing at those skills and `bob check`.

Expected values are literals from docs/SPEC.md and the vendored upstream
pin, not derived from the files under test.
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = (ROOT / "docs" / "SPEC.md").read_text(encoding="utf-8")

ORIGIN_URL = "https://github.com/mattpocock/skills"
ORIGIN_COMMIT = "49dd158d1076134a641b33efb035946536778336"

# Verbatim CLI surface from docs/SPEC.md (Implementation Decisions).
SPEC_CLI_LINES = [
    "bob check   [--base REF] [--gates crap,dry,deps,mutate] [--config bob.yaml] [--format md|json|both] [--out .bob/]",
    "bob crap    [--base REF] [--threshold N] [--coverage-file PATH]",
    "bob dry     [--base REF]",
    "bob deps",
    "bob mutate  [--base REF] [--since-last-run] [--max-workers N]",
    "bob report  [--in .bob/] [--out .bob/report.md]",
    'bob waive   <mutant-id|function> --reason "texto de uma linha"',
    "bob doctor  # verifica ferramentas e versões instaladas",
    "bob <comando> [--lang en|pt-BR]  # idioma da saída (padrão: en)",
]

SPEC_EXIT_LINES = [
    "`0` passou",
    "`1` algum gate falhou (limite violado)",
    "`2` baseline quebrado (testes falham antes de medir)",
    "`3` mutante sobrevivente sem waiver",
    "`4` erro de configuração ou ferramenta ausente",
]

SPEC_NAMED_POCOCK_SKILLS = {
    "grill-me": "productivity/grill-me/SKILL.md",
    "to-spec": "engineering/to-spec/SKILL.md",
    "to-tickets": "engineering/to-tickets/SKILL.md",
    "implement-spec": "engineering/implement-spec/SKILL.md",
    "tdd": "engineering/tdd/SKILL.md",
    "code-review": "engineering/code-review/SKILL.md",
    "pr": "engineering/pr/SKILL.md",
    "writing-for-agents": "productivity/writing-for-agents/SKILL.md",
}

FRONTMATTER_RE = re.compile(r"\A---\n(.*?)\n---\n", re.DOTALL)
NAME_RE = re.compile(r"^name:\s*[\"']?([a-z0-9-]+)[\"']?\s*$", re.MULTILINE)
DESC_RE = re.compile(
    r"^description:\s*(?:>-?\s*\n(?:[ \t]+.+\n)+|[\"'].*?[\"']|.+)$",
    re.MULTILINE,
)
COMMIT_RE = re.compile(r"\b[0-9a-f]{40}\b")


def _frontmatter(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    match = FRONTMATTER_RE.match(text)
    if match is None:
        raise AssertionError(f"{path} is missing YAML frontmatter")
    return match.group(1)


class SpecLiteralsStillInSpec(unittest.TestCase):
    """The pinned literals must still be the text in docs/SPEC.md."""

    def test_cli_lines_are_in_spec(self) -> None:
        for line in SPEC_CLI_LINES:
            with self.subTest(line=line):
                self.assertIn(line, SPEC)

    def test_exit_lines_are_in_spec(self) -> None:
        for line in SPEC_EXIT_LINES:
            with self.subTest(line=line):
                self.assertIn(line, SPEC)


class VendorAttribution(unittest.TestCase):
    def test_license_is_upstream_mit(self) -> None:
        license_text = (ROOT / "skills/vendor/mattpocock/LICENSE").read_text(
            encoding="utf-8"
        )
        self.assertIn("MIT License", license_text)
        self.assertIn("Matt Pocock", license_text)

    def test_notice_records_source_and_commit(self) -> None:
        notice = (ROOT / "skills/vendor/mattpocock/NOTICE").read_text(
            encoding="utf-8"
        )
        self.assertIn(ORIGIN_URL, notice)
        self.assertIn(ORIGIN_COMMIT, notice)
        self.assertRegex(notice, COMMIT_RE)

    def test_named_pocock_skills_are_present(self) -> None:
        vendor = ROOT / "skills/vendor/mattpocock"
        for name, relpath in SPEC_NAMED_POCOCK_SKILLS.items():
            skill = vendor / relpath
            with self.subTest(skill=name):
                self.assertTrue(skill.is_file(), f"missing {skill}")
                fm = _frontmatter(skill)
                match = NAME_RE.search(fm)
                self.assertIsNotNone(match, f"{skill} has no name")
                self.assertEqual(match.group(1), name)


class AgentSkillsFrontmatter(unittest.TestCase):
    def test_bob_check_frontmatter(self) -> None:
        self._assert_skill(ROOT / "skills/bob-check/SKILL.md", "bob-check")

    def test_review_report_frontmatter(self) -> None:
        self._assert_skill(
            ROOT / "skills/review-report/SKILL.md", "review-report"
        )

    def _assert_skill(self, path: Path, expected_name: str) -> None:
        self.assertTrue(path.is_file(), f"missing {path}")
        self.assertEqual(path.parent.name, expected_name)
        fm = _frontmatter(path)
        match = NAME_RE.search(fm)
        self.assertIsNotNone(match)
        self.assertEqual(match.group(1), expected_name)
        self.assertLessEqual(len(match.group(1)), 64)
        self.assertIsNotNone(DESC_RE.search(fm), f"{path} has no description")


class BobCheckCliSurface(unittest.TestCase):
    def test_quotes_spec_cli_and_exit_codes(self) -> None:
        body = (ROOT / "skills/bob-check/SKILL.md").read_text(encoding="utf-8")
        for line in SPEC_CLI_LINES:
            with self.subTest(line=line):
                self.assertIn(line, body)
        for line in SPEC_EXIT_LINES:
            with self.subTest(line=line):
                self.assertIn(line, body)
        self.assertIn("schema_version: 1", body)
        self.assertIn("crap,dry,deps", body)
        self.assertIn(".bob/", body)


class ReviewReportPrBody(unittest.TestCase):
    def test_writes_the_pr_body_around_the_report(self) -> None:
        body = (ROOT / "skills/review-report/SKILL.md").read_text(encoding="utf-8")
        self.assertIn(".bob/report.md", body)
        for heading in ("## Summary", "## Evidence", "## Merge Danger"):
            with self.subTest(heading=heading):
                self.assertIn(heading, body)
        self.assertIn("Onde focar o review", body)
        self.assertIn("schema_version: 1", body)


class AgentsIndex(unittest.TestCase):
    def test_points_at_skills_and_bob_check(self) -> None:
        text = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        self.assertIn("bob-check", text)
        self.assertIn("review-report", text)
        self.assertIn("skills/vendor/mattpocock", text)
        self.assertIn("bob check", text)


if __name__ == "__main__":
    unittest.main()
