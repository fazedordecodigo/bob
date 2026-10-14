from __future__ import annotations

import ast
import enum
import json
import os
import subprocess
from dataclasses import dataclass
from fnmatch import fnmatch
from pathlib import Path, PurePosixPath
from typing import Literal, Mapping, Sequence

from bob_quality.adapters.eslint_tests import EslintHit, EslintParseError, parse_eslint_json
from bob_quality.config import Config, SourceLanguage
from bob_quality.messages import Text, msg
from bob_quality.models import GateResult, TestSmell
from bob_quality.waivers import Waiver, load_waivers

WarningContribution = Literal[0]

PYTHON_EMPTY = "empty-test"
PYTHON_DISABLED = "disabled-test"
PYTHON_SLEEP = "sleep"
PYTHON_MISSING_ASSERT = "missing-assert"
SKIP_ATTRS = frozenset({"skip", "skipif", "skipIf", "skipUnless", "xfail", "importorskip"})
SLEEP_NAMES = frozenset({"sleep"})
ASSERTION_NAMES = frozenset({"fail", "raises", "warns", "deprecated_call"})
_PY_TEST_NAMES = ("test_*.py", "*_test.py")
_NOT_PY_TESTS = frozenset({"conftest.py", "__init__.py"})
_TS_TEST_SUFFIXES = (
    ".test.ts",
    ".test.tsx",
    ".test.js",
    ".test.jsx",
    ".test.mjs",
    ".test.cjs",
    ".spec.ts",
    ".spec.tsx",
    ".spec.js",
    ".spec.jsx",
    ".spec.mjs",
    ".spec.cjs",
)
_TS_SOURCE_SUFFIXES = (".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs")
_PLUGIN_MARKERS = (
    "eslint-plugin-jest",
    "eslint-plugin-vitest",
    "plugin:jest/",
    "plugin:vitest/",
)
_ESLINT_CONFIG_NAMES = frozenset(
    {
        "eslint.config.js",
        "eslint.config.mjs",
        "eslint.config.cjs",
        "eslint.config.ts",
        "eslint.config.mts",
        "eslint.config.cts",
        ".eslintrc",
        ".eslintrc.js",
        ".eslintrc.cjs",
        ".eslintrc.json",
        ".eslintrc.yml",
        ".eslintrc.yaml",
    }
)
_WALK_SKIP = frozenset({"node_modules", "dist", ".git", ".bob"})
_MEASURED_EXITS = frozenset({0, 1})
_NESTED = (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
_TEST_FN = (ast.FunctionDef, ast.AsyncFunctionDef)


class BodyKind(enum.Enum):
    EMPTY = "EMPTY"
    NO_ASSERT = "NO_ASSERT"
    HAS_ASSERT = "HAS_ASSERT"


_BODY_RULE = {
    BodyKind.EMPTY: PYTHON_EMPTY,
    BodyKind.NO_ASSERT: PYTHON_MISSING_ASSERT,
}


@dataclass(frozen=True)
class LanguageMeasured:
    language: SourceLanguage
    findings: tuple[TestSmell, ...]
    eslint_version: str | None = None


@dataclass(frozen=True)
class LanguageBroken:
    language: Literal["typescript"]
    detail: Text
    eslint_version: str | None = None


@dataclass(frozen=True)
class LanguageSkipped:
    language: Literal["typescript"]


LanguageOutcome = LanguageMeasured | LanguageBroken | LanguageSkipped


def waiver_id(smell: TestSmell) -> str:
    return f"tests:{smell.file}:{smell.line}:{smell.rule}"


def test_smell(
    file: str,
    line: int,
    rule: str,
    changed: frozenset[int],
) -> TestSmell | None:
    if line not in changed:
        return None
    return TestSmell(file, line, rule)


def apply_test_waivers(
    findings: tuple[TestSmell, ...],
    waivers: Sequence[Waiver],
) -> tuple[TestSmell, ...]:
    reasons = {item.id: item.reason for item in waivers}
    applied: list[TestSmell] = []
    for smell in findings:
        reason = reasons.get(waiver_id(smell))
        if reason is None:
            applied.append(smell)
            continue
        applied.append(TestSmell(smell.file, smell.line, smell.rule, reason))
    return tuple(applied)


def fold_outcomes(
    outcomes: tuple[LanguageOutcome, ...],
) -> tuple[GateResult, tuple[TestSmell, ...]]:
    measured, broken = _split_outcomes(outcomes)
    detail = _join_details(tuple(item.detail for item in broken))
    if not measured:
        return _unmeasured(detail)
    findings = _sorted_findings(measured)
    return _verdict(findings, detail), findings


def run_test_smells_gate(
    cwd: Path,
    config: Config,
    diff_lines: Mapping[str, set[int]],
) -> tuple[GateResult, tuple[TestSmell, ...], WarningContribution, dict[str, str]]:
    waivers = load_waivers(cwd)
    outcomes = _outcomes(config, cwd, diff_lines)
    result, findings = fold_outcomes(_waived(outcomes, waivers))
    return result, findings, 0, _versions(outcomes)


def measure_python(
    cwd: Path,
    diff_lines: Mapping[str, set[int]],
) -> LanguageMeasured:
    findings: list[TestSmell] = []
    for relative in changed_test_paths(diff_lines, "python"):
        source = _read_source(cwd / relative)
        if source is None:
            continue
        changed = frozenset(diff_lines[relative])
        findings.extend(python_smells(source, relative, changed))
    return LanguageMeasured("python", tuple(findings))


def changed_test_paths(
    diff_lines: Mapping[str, set[int]],
    language: SourceLanguage,
) -> tuple[str, ...]:
    if language == "python":
        return tuple(sorted(path for path in diff_lines if _is_python_test(path)))
    if language == "typescript":
        return tuple(sorted(path for path in diff_lines if _is_typescript_test(path)))
    raise AssertionError(language)


def python_smells(source: str, file: str, changed: frozenset[int]) -> tuple[TestSmell, ...]:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return ()
    smells: list[TestSmell] = []
    module_markers = _block_markers(tree.body)
    for node in tree.body:
        if _is_test_function(node):
            smells.extend(_function_smells(file, node, changed, module_markers))
            continue
        if isinstance(node, ast.ClassDef) and node.name.startswith("Test"):
            inherited = [
                *module_markers,
                *_decorator_markers(node.decorator_list),
                *_block_markers(node.body),
            ]
            for item in node.body:
                if _is_test_function(item):
                    smells.extend(_function_smells(file, item, changed, inherited))
    return tuple(sorted(_unique(smells), key=_by_location))


def measure_typescript(
    cwd: Path,
    diff_lines: Mapping[str, set[int]],
) -> LanguageOutcome:
    if not eslint_configured(cwd):
        return LanguageSkipped("typescript")
    paths = changed_test_paths(diff_lines, "typescript")
    if not paths:
        return LanguageMeasured("typescript", ())
    return _measure_eslint(cwd, diff_lines, paths)


def eslint_configured(cwd: Path) -> bool:
    for path in _config_files(cwd):
        if path.name == "package.json":
            mentions = _package_mentions_plugin(path)
        else:
            mentions = _text_mentions_plugin(path)
        if mentions:
            return True
    return False


def _outcomes(
    config: Config,
    cwd: Path,
    diff_lines: Mapping[str, set[int]],
) -> tuple[LanguageOutcome, ...]:
    found: list[LanguageOutcome] = []
    for language in config.languages:
        if language == "python":
            found.append(measure_python(cwd, diff_lines))
            continue
        if language == "typescript":
            found.append(measure_typescript(cwd, diff_lines))
            continue
        raise AssertionError(language)
    return tuple(found)


def _waived(
    outcomes: tuple[LanguageOutcome, ...],
    waivers: Sequence[Waiver],
) -> tuple[LanguageOutcome, ...]:
    return tuple(_waive_one(outcome, waivers) for outcome in outcomes)


def _waive_one(outcome: LanguageOutcome, waivers: Sequence[Waiver]) -> LanguageOutcome:
    if isinstance(outcome, LanguageMeasured):
        return LanguageMeasured(
            outcome.language,
            apply_test_waivers(outcome.findings, waivers),
            outcome.eslint_version,
        )
    if isinstance(outcome, (LanguageBroken, LanguageSkipped)):
        return outcome
    raise AssertionError(type(outcome))


def _split_outcomes(
    outcomes: tuple[LanguageOutcome, ...],
) -> tuple[tuple[LanguageMeasured, ...], tuple[LanguageBroken, ...]]:
    measured: list[LanguageMeasured] = []
    broken: list[LanguageBroken] = []
    for outcome in outcomes:
        _collect_outcome(outcome, measured, broken)
    return tuple(measured), tuple(broken)


def _collect_outcome(
    outcome: LanguageOutcome,
    measured: list[LanguageMeasured],
    broken: list[LanguageBroken],
) -> None:
    if isinstance(outcome, LanguageMeasured):
        measured.append(outcome)
        return
    if isinstance(outcome, LanguageBroken):
        broken.append(outcome)
        return
    if isinstance(outcome, LanguageSkipped):
        return
    raise AssertionError(type(outcome))


def _unmeasured(detail: Text | None) -> tuple[GateResult, tuple[TestSmell, ...]]:
    reason = detail if detail is not None else msg("test_smells.nothing_measured")
    return GateResult("test_smells", "not_run", reason), ()


def _sorted_findings(measured: tuple[LanguageMeasured, ...]) -> tuple[TestSmell, ...]:
    smells = [smell for item in measured for smell in item.findings]
    return tuple(sorted(smells, key=_by_location))


def _verdict(findings: tuple[TestSmell, ...], detail: Text | None) -> GateResult:
    unwaived = _unwaived_count(findings)
    if unwaived == 0:
        return GateResult("test_smells", "passed", detail)
    return GateResult("test_smells", "warn", _warn_reason(unwaived, detail))


def _unwaived_count(findings: tuple[TestSmell, ...]) -> int:
    return sum(1 for smell in findings if smell.waiver is None)


def _warn_reason(unwaived: int, detail: Text | None) -> Text:
    count = msg(_count_key(unwaived), count=unwaived)
    if detail is None:
        return count
    return msg("test_smells.with_detail", head=count, detail=detail)


def _measure_eslint(
    cwd: Path,
    diff_lines: Mapping[str, set[int]],
    paths: tuple[str, ...],
) -> LanguageOutcome:
    binary = cwd / "node_modules" / ".bin" / "eslint"
    version = _version_when_present(cwd, binary)
    if not binary.is_file():
        return LanguageBroken("typescript", msg("test_smells.eslint_missing"))
    completed = _completed_eslint(cwd, binary, paths, version)
    if isinstance(completed, LanguageBroken):
        return completed
    return _hits_to_measured(cwd, diff_lines, completed.stdout, version)


def _version_when_present(cwd: Path, binary: Path) -> str | None:
    if binary.is_file():
        return _eslint_package_version(cwd)
    return None


def _completed_eslint(
    cwd: Path,
    binary: Path,
    paths: tuple[str, ...],
    version: str | None,
) -> subprocess.CompletedProcess[str] | LanguageBroken:
    try:
        completed = _spawn_eslint(cwd, binary, paths)
    except OSError:
        return LanguageBroken("typescript", msg("test_smells.eslint_start"), version)
    except UnicodeError:
        return LanguageBroken("typescript", msg("test_smells.eslint_unparsed"), version)
    if completed.returncode not in _MEASURED_EXITS:
        return _bad_exit(completed.returncode, version)
    return completed


def _bad_exit(code: int, version: str | None) -> LanguageBroken:
    return LanguageBroken("typescript", msg("test_smells.eslint_bad_exit", code=code), version)


def _hits_to_measured(
    cwd: Path,
    diff_lines: Mapping[str, set[int]],
    stdout: str,
    version: str | None,
) -> LanguageOutcome:
    try:
        hits = parse_eslint_json(stdout)
    except EslintParseError:
        return LanguageBroken("typescript", msg("test_smells.eslint_unparsed"), version)
    return LanguageMeasured("typescript", _smells_from_hits(cwd, diff_lines, hits), version)


def _smells_from_hits(
    cwd: Path,
    diff_lines: Mapping[str, set[int]],
    hits: tuple[EslintHit, ...],
) -> tuple[TestSmell, ...]:
    findings: list[TestSmell] = []
    for hit in hits:
        smell = _smell_on_diff(cwd, diff_lines, hit)
        if smell is not None:
            findings.append(smell)
    return tuple(findings)


def _smell_on_diff(
    cwd: Path,
    diff_lines: Mapping[str, set[int]],
    hit: EslintHit,
) -> TestSmell | None:
    relative = _repo_relative(cwd, hit.file)
    if relative is None:
        return None
    changed = frozenset(diff_lines.get(relative, ()))
    return test_smell(relative, hit.line, hit.rule, changed)


def _versions(outcomes: tuple[LanguageOutcome, ...]) -> dict[str, str]:
    versions: dict[str, str] = {}
    for outcome in outcomes:
        version = _eslint_version(outcome)
        if version is not None:
            versions["eslint"] = version
    return versions


def _eslint_version(outcome: LanguageOutcome) -> str | None:
    if isinstance(outcome, LanguageSkipped):
        return None
    if isinstance(outcome, (LanguageMeasured, LanguageBroken)):
        return outcome.eslint_version
    raise AssertionError(type(outcome))


def _join_details(details: tuple[Text, ...]) -> Text | None:
    if not details:
        return None
    joined = details[0]
    for detail in details[1:]:
        joined = msg("probe.joined", first=joined, second=detail)
    return joined


def _count_key(unwaived: int) -> str:
    if unwaived == 1:
        return "test_smells.one"
    return "test_smells.many"


def _by_location(smell: TestSmell) -> tuple[str, int, str]:
    return smell.file, smell.line, smell.rule


def _read_source(path: Path) -> str | None:
    try:
        return path.read_bytes().decode()
    except (OSError, UnicodeError):
        return None


def _is_python_test(path: str) -> bool:
    name = PurePosixPath(path).name
    if name in _NOT_PY_TESTS:
        return False
    return any(fnmatch(name, pattern) for pattern in _PY_TEST_NAMES)


def _is_typescript_test(path: str) -> bool:
    pure = PurePosixPath(path)
    name = pure.name
    if name.endswith(".d.ts"):
        return False
    if name.endswith(_TS_TEST_SUFFIXES):
        return True
    return "__tests__" in pure.parts and name.endswith(_TS_SOURCE_SUFFIXES)


def _spawn_eslint(
    cwd: Path,
    binary: Path,
    paths: tuple[str, ...],
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(binary), "--format", "json", *paths],
        cwd=cwd,
        capture_output=True,
        text=True,
        stdin=subprocess.DEVNULL,
    )


def _eslint_package_version(cwd: Path) -> str | None:
    path = cwd / "node_modules" / "eslint" / "package.json"
    try:
        loaded = json.loads(path.read_bytes().decode())
    except (OSError, UnicodeError, json.JSONDecodeError):
        return None
    if not isinstance(loaded, dict):
        return None
    version = loaded.get("version")
    if isinstance(version, str):
        return version
    return None


def _config_files(cwd: Path):
    for root, dirs, files in os.walk(cwd):
        dirs[:] = [name for name in dirs if name not in _WALK_SKIP]
        for name in files:
            if name in _ESLINT_CONFIG_NAMES or name == "package.json":
                yield Path(root) / name


def _text_mentions_plugin(path: Path) -> bool:
    try:
        text = path.read_bytes().decode()
    except (OSError, UnicodeError):
        return False
    return any(marker in text for marker in _PLUGIN_MARKERS)


def _package_mentions_plugin(path: Path) -> bool:
    try:
        loaded = json.loads(path.read_bytes().decode())
    except (OSError, UnicodeError, json.JSONDecodeError):
        return False
    if not isinstance(loaded, dict) or "eslintConfig" not in loaded:
        return False
    blob = json.dumps(loaded["eslintConfig"])
    return any(marker in blob for marker in _PLUGIN_MARKERS)


def _repo_relative(cwd: Path, raw: str) -> str | None:
    root = cwd.resolve()
    path = Path(raw)
    if path.is_absolute():
        candidate = path
    else:
        candidate = root / path
    try:
        relative = candidate.resolve().relative_to(root)
    except ValueError:
        return None
    if not relative.parts:
        return None
    return relative.as_posix()


def _is_test_function(node: ast.AST) -> bool:
    return isinstance(node, _TEST_FN) and node.name.startswith("test_")


def _function_smells(
    file: str,
    fn: ast.FunctionDef | ast.AsyncFunctionDef,
    changed: frozenset[int],
    inherited: list[ast.AST],
) -> list[TestSmell]:
    markers = [*inherited, *_decorator_markers(fn.decorator_list), *_skip_calls(fn.body)]
    smells: list[TestSmell] = []
    for marker in markers:
        smell = test_smell(file, marker.lineno, PYTHON_DISABLED, changed)
        if smell is not None:
            smells.append(smell)
    if not markers:
        smells.extend(_body_smell(file, fn, changed))
    smells.extend(_sleep_smells(file, fn.body, changed))
    return smells


def _body_smell(
    file: str,
    fn: ast.FunctionDef | ast.AsyncFunctionDef,
    changed: frozenset[int],
) -> list[TestSmell]:
    rule = _BODY_RULE.get(_body_kind(fn.body))
    if rule is None:
        return []
    line = _body_line(fn, changed)
    if line is None:
        return []
    smell = test_smell(file, line, rule, changed)
    if smell is None:
        return []
    return [smell]


def _body_kind(body: list[ast.stmt]) -> BodyKind:
    if all(_is_empty_statement(stmt) for stmt in body):
        return BodyKind.EMPTY
    if _contains_assert(body):
        return BodyKind.HAS_ASSERT
    return BodyKind.NO_ASSERT


def _is_empty_statement(stmt: ast.stmt) -> bool:
    if isinstance(stmt, ast.Pass):
        return True
    if not isinstance(stmt, ast.Expr) or not isinstance(stmt.value, ast.Constant):
        return False
    return stmt.value.value is Ellipsis or isinstance(stmt.value.value, str)


def _contains_assert(body: list[ast.stmt]) -> bool:
    return any(_statement_asserts(stmt) for stmt in body)


def _statement_asserts(stmt: ast.stmt) -> bool:
    if isinstance(stmt, _NESTED):
        return False
    for node in _walk_outside_nested(stmt):
        if isinstance(node, ast.Assert):
            return True
        if isinstance(node, ast.Call) and _call_is_assertion(node):
            return True
    return False


def _walk_outside_nested(node: ast.AST):
    yield node
    if isinstance(node, _NESTED):
        return
    for child in ast.iter_child_nodes(node):
        yield from _walk_outside_nested(child)


def _call_is_assertion(node: ast.Call) -> bool:
    name = _terminal_name(node.func)
    return name is not None and _is_assertion_name(name)


def _is_assertion_name(name: str) -> bool:
    if name in ASSERTION_NAMES:
        return True
    if not name.startswith("assert"):
        return False
    rest = name.removeprefix("assert")
    if rest == "":
        return True
    return rest[0] == "_" or rest[0].isupper()


def _body_line(
    fn: ast.FunctionDef | ast.AsyncFunctionDef,
    changed: frozenset[int],
) -> int | None:
    start = fn.lineno
    if fn.decorator_list:
        start = min(start, *(item.lineno for item in fn.decorator_list))
    end = fn.end_lineno if fn.end_lineno is not None else fn.lineno
    overlap = {line for line in changed if start <= line <= end}
    if not overlap:
        return None
    if fn.lineno in overlap:
        return fn.lineno
    return min(overlap)


def _sleep_smells(
    file: str,
    body: list[ast.stmt],
    changed: frozenset[int],
) -> list[TestSmell]:
    smells: list[TestSmell] = []
    for stmt in body:
        for node in ast.walk(stmt):
            if not isinstance(node, ast.Call):
                continue
            if _terminal_name(node.func) not in SLEEP_NAMES:
                continue
            smell = test_smell(file, node.lineno, PYTHON_SLEEP, changed)
            if smell is not None:
                smells.append(smell)
    return smells


def _block_markers(body: list[ast.stmt]) -> list[ast.AST]:
    found: list[ast.AST] = []
    for stmt in body:
        if isinstance(stmt, ast.Assign) and any(_is_pytestmark(target) for target in stmt.targets):
            found.extend(_skip_values(stmt.value))
            continue
        if isinstance(stmt, ast.AnnAssign) and _is_pytestmark(stmt.target) and stmt.value is not None:
            found.extend(_skip_values(stmt.value))
            continue
        if isinstance(stmt, ast.Expr):
            found.extend(_skip_values(stmt.value))
    return found


def _decorator_markers(decorators: list[ast.expr]) -> list[ast.AST]:
    return [item for item in decorators if _terminal_name(item) in SKIP_ATTRS]


def _skip_calls(body: list[ast.stmt]) -> list[ast.Call]:
    found: list[ast.Call] = []
    for stmt in body:
        for node in ast.walk(stmt):
            if isinstance(node, ast.Call) and _terminal_name(node.func) in SKIP_ATTRS:
                found.append(node)
    return found


def _skip_values(node: ast.AST) -> list[ast.AST]:
    if isinstance(node, (ast.List, ast.Tuple, ast.Set)):
        found: list[ast.AST] = []
        for item in node.elts:
            found.extend(_skip_values(item))
        return found
    if _terminal_name(node) in SKIP_ATTRS:
        return [node]
    return []


def _is_pytestmark(node: ast.AST) -> bool:
    return isinstance(node, ast.Name) and node.id == "pytestmark"


def _terminal_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Call):
        return _terminal_name(node.func)
    if isinstance(node, ast.Attribute):
        return node.attr
    if isinstance(node, ast.Name):
        return node.id
    return None


def _unique(smells: list[TestSmell]) -> list[TestSmell]:
    seen: set[tuple[str, int, str]] = set()
    chosen: list[TestSmell] = []
    for smell in smells:
        key = (smell.file, smell.line, smell.rule)
        if key in seen:
            continue
        seen.add(key)
        chosen.append(smell)
    return chosen
