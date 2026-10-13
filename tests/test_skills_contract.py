from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = (ROOT / "docs" / "SPEC.md").read_text(encoding="utf-8")

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

SKILL_CLI_LINES = [
    "bob check   [--base REF] [--gates crap,dry,deps,mutate] [--config bob.yaml] [--format md|json|both] [--out .bob/]",
    "bob crap    [--base REF] [--threshold N] [--coverage-file PATH]",
    "bob dry     [--base REF]",
    "bob deps",
    "bob mutate  [--base REF] [--since-last-run] [--max-workers N]",
    'bob waive   <mutant-id|function> --reason "texto de uma linha"',
    "bob doctor  # verifica ferramentas e versões instaladas",
    "bob <comando> [--lang en|pt-BR]  # idioma da saída (padrão: en)",
]
REPORT_COMMAND = "bob check --format both"

SPEC_EXIT_LINES = [
    "`0` passou",
    "`1` algum gate falhou (limite violado)",
    "`2` baseline quebrado (testes falham antes de medir)",
    "`3` mutante sobrevivente sem waiver",
    "`4` erro de configuração ou ferramenta ausente",
]

FRONTMATTER_RE = re.compile(r"\A---\n(.*?)\n---\n", re.DOTALL)
NAME_RE = re.compile(r"^name:\s*[\"']?([a-z0-9-]+)[\"']?\s*$", re.MULTILINE)
DESC_RE = re.compile(
    r"^description:\s*(?:>-?\s*\n(?:[ \t]+.+\n)+|[\"'].*?[\"']|.+)$",
    re.MULTILINE,
)


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
        for line in SKILL_CLI_LINES:
            with self.subTest(line=line):
                self.assertIn(line, body)
        self.assertIn(REPORT_COMMAND, body)
        self.assertNotIn("bob report", body)
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
        self.assertIn(REPORT_COMMAND, body)
        self.assertNotIn("bob report", body)


class AgentsIndex(unittest.TestCase):
    def test_points_at_skills_and_bob_check(self) -> None:
        text = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        self.assertIn("bob-check", text)
        self.assertIn("review-report", text)
        self.assertIn("harden", text)
        self.assertIn("bob check", text)


class InvalidCliUsageInSkills(unittest.TestCase):
    _BULLET = "- `4` erro de configuração ou ferramenta ausente"
    _PHRASE_LINE = (
        "O `4` é erro de configuração ou ferramenta ausente, ou uso inválido da CLI."
    )
    _PREDICATE_LINE = (
        "Uso inválido: o stderr começa com `usage: bob`, contém `error:` "
        "e não menciona baseline. Essa execução não grava relatório. "
        "Um arquivo `.bob/` já presente não é desta execução. "
        "Não é o exit `2`. A ajuda (`-h`, `--help`) sai com `0`. "
        "Catálogo em docs/exit-codes.md#exit-4."
    )
    _BOB_STEP_1 = (
        "1. Rodar `bob check --format both` com o `--base` do PR. "
        "Se o exit é `4` e o stderr começa com `usage: bob`, contém `error:` "
        "e não menciona baseline, seguir o passo 5 e repetir com o argv corrigido. "
        "Um `.bob/report.json` de outra corrida não fecha esse caso. "
        "Fora esse caso, feito quando o processo devolve um exit code "
        "e `.bob/report.json` existe."
    )
    _BOB_STEP_5 = (
        "5. Exit `4` com stderr que começa com `usage: bob`, contém `error:` "
        "e não menciona baseline: corrigir o argv e repetir. "
        "Não é o exit `2`. `bob doctor` não se aplica. "
        "Não ler `.bob/` deixado por outra corrida como veredito desta. "
        "Senão, `bob doctor` e corrigir ferramenta ou config. "
        "Feito quando o check é reexecutado."
    )
    _REVIEW_STEP_1 = (
        "1. Confirmar `.bob/report.md`. Se a execução que acabou de rodar saiu `4` "
        "e o stderr começa com `usage: bob`, contém `error:` e não menciona baseline, "
        "não escrever o PR a partir do arquivo e não chamar `bob check` de novo "
        "com o mesmo argv. Não é o exit `2`. Seguir a skill `bob-check`. "
        "Fora esse caso, se `.bob/report.md` falta, gerar com `bob check --format both`. "
        "Feito quando `.bob/report.md` existe e a execução não caiu no uso inválido acima."
    )

    def test_spec_bullet_stays_a_whole_line_and_the_next_lines_classify(self) -> None:
        for relative in (
            "skills/bob-check/SKILL.md",
            "skills/review-report/SKILL.md",
        ):
            lines = (ROOT / relative).read_text(encoding="utf-8").splitlines()
            with self.subTest(relative=relative):
                index = lines.index(self._BULLET)
                self.assertEqual(lines[index + 1], self._PHRASE_LINE)
                self.assertEqual(lines[index + 2], self._PREDICATE_LINE)
                self.assertIn("ou uso inválido da CLI", lines[index + 1])

    def test_procedures_follow_the_predicate(self) -> None:
        bob = (ROOT / "skills/bob-check/SKILL.md").read_text(encoding="utf-8")
        review = (ROOT / "skills/review-report/SKILL.md").read_text(encoding="utf-8")
        self.assertIn(self._BOB_STEP_1, bob)
        self.assertIn(self._BOB_STEP_5, bob)
        self.assertIn(self._REVIEW_STEP_1, review)


if __name__ == "__main__":
    unittest.main()
