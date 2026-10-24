import json
import os
from pathlib import Path

import pytest

import bob_quality.test_smells as smells
from bob_quality.adapters.eslint_tests import EslintHit, EslintParseError, parse_eslint_json
from bob_quality.messages import msg
from bob_quality.models import TestSmell as SmellRow

_FILE = "src/gap.test.ts"


def test_eslint_json_keeps_prefix_hits_on_changed_lines(tmp_path: Path) -> None:
    saved = os.dup(0)
    read_fd, write_fd = os.pipe()
    os.dup2(read_fd, 0)
    try:
        _assert_prefix_hits(tmp_path)
    finally:
        os.dup2(saved, 0)
        os.close(saved)
        os.close(read_fd)
        os.close(write_fd)


def _assert_prefix_hits(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    target = (repo / _FILE).resolve().as_posix()
    payload = [
        {
            "filePath": target,
            "messages": [
                {"ruleId": "jest/expect-expect", "line": 1},
                {"ruleId": "vitest/no-commented-out-tests", "line": 1},
                {"ruleId": "eslint/no-undef", "line": 1},
                {"ruleId": "jest/no-disabled-tests", "line": 99},
                {"ruleId": "jest/no-focused-tests", "line": True},
                {"ruleId": "jest/no-conditional-expect", "line": 0},
                {"ruleId": 1, "line": 1},
                "nope",
            ],
        },
        {"filePath": _FILE, "messages": 1},
        {
            "filePath": f"./{_FILE}",
            "messages": [{"ruleId": "jest/valid-expect", "line": 1}],
        },
        {
            "filePath": "/etc/passwd",
            "messages": [{"ruleId": "jest/expect-expect", "line": 1}],
        },
        {
            "filePath": repo.resolve().as_posix(),
            "messages": [{"ruleId": "jest/expect-expect", "line": 1}],
        },
        {
            "filePath": "src/other.test.ts",
            "messages": [{"ruleId": "jest/expect-expect", "line": 1}],
        },
        "nope",
    ]
    _install(repo, _script(payload, 1), "9.14.0")

    measured = smells.measure_typescript(repo, {_FILE: {1}})

    assert measured == smells.LanguageMeasured(
        "typescript",
        (
            SmellRow(_FILE, 1, "jest/expect-expect"),
            SmellRow(_FILE, 1, "vitest/no-commented-out-tests"),
            SmellRow(_FILE, 1, "jest/valid-expect"),
        ),
        "9.14.0",
    )


def test_exit_zero_with_an_empty_list_is_measured(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    _install(repo, _script([], 0), "9.14.0")

    assert smells.measure_typescript(repo, {_FILE: {1}}) == smells.LanguageMeasured(
        "typescript", (), "9.14.0"
    )


def test_exit_two_stays_broken_and_keeps_the_version(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    _install(repo, _script([], 2), "9.14.0")

    assert smells.measure_typescript(repo, {_FILE: {1}}) == smells.LanguageBroken(
        "typescript", msg("test_smells.eslint_bad_exit", code=2), "9.14.0"
    )


def test_a_missing_binary_names_the_missing_tool(tmp_path: Path) -> None:
    repo = _repo(tmp_path)

    assert smells.measure_typescript(repo, {_FILE: {1}}) == smells.LanguageBroken(
        "typescript", msg("test_smells.eslint_missing"), None
    )


def test_a_binary_that_cannot_start_names_the_start_failure(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    bindir = repo / "node_modules" / ".bin"
    bindir.mkdir(parents=True)
    binary = bindir / "eslint"
    binary.write_text("not a program\n", encoding="utf-8")
    binary.chmod(0o644)
    package = repo / "node_modules" / "eslint"
    package.mkdir(parents=True)
    (package / "package.json").write_text('{"version": "9.14.0"}\n', encoding="utf-8")

    assert smells.measure_typescript(repo, {_FILE: {1}}) == smells.LanguageBroken(
        "typescript", msg("test_smells.eslint_start"), "9.14.0"
    )


def test_stdout_that_is_not_utf8_stays_unparsed(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    script = "#!/usr/bin/env python3\nimport sys\nsys.stdout.buffer.write(b'\\xff')\n"
    _install(repo, script, "9.14.0")

    assert smells.measure_typescript(repo, {_FILE: {1}}) == smells.LanguageBroken(
        "typescript", msg("test_smells.eslint_unparsed"), "9.14.0"
    )


def test_text_that_is_not_json_stays_unparsed(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    _install(repo, _raw("nope", 0), "9.14.0")

    assert smells.measure_typescript(repo, {_FILE: {1}}) == smells.LanguageBroken(
        "typescript", msg("test_smells.eslint_unparsed"), "9.14.0"
    )


def test_parse_rejects_a_non_list_and_bad_json() -> None:
    with pytest.raises(EslintParseError) as bad_json:
        parse_eslint_json("{")
    with pytest.raises(EslintParseError) as not_list:
        parse_eslint_json("{}")

    assert bad_json.value.args[0] == msg("test_smells.eslint_unparsed")
    assert not_list.value.args[0] == msg("test_smells.eslint_unparsed")


def test_parse_keeps_only_prefixed_rules_with_a_real_line() -> None:
    raw = json.dumps(
        [
            {
                "filePath": _FILE,
                "messages": [
                    {"ruleId": "jest/expect-expect", "line": 1},
                    {"ruleId": "vitest/no-commented-out-tests", "line": 2},
                    {"ruleId": "eslint/no-undef", "line": 1},
                    {"ruleId": "jest/no-focused-tests", "line": True},
                    {"ruleId": "jest/no-conditional-expect", "line": 0},
                ],
            }
        ]
    )

    assert parse_eslint_json(raw) == (
        EslintHit(_FILE, 1, "jest/expect-expect"),
        EslintHit(_FILE, 2, "vitest/no-commented-out-tests"),
    )


def _repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "eslint.config.js").write_text("// eslint-plugin-jest\n", encoding="utf-8")
    source = repo / _FILE
    source.parent.mkdir()
    source.write_text("export {}\n", encoding="utf-8")
    return repo


def _install(repo: Path, script: str, version: str) -> None:
    bindir = repo / "node_modules" / ".bin"
    bindir.mkdir(parents=True)
    binary = bindir / "eslint"
    binary.write_text(script, encoding="utf-8")
    binary.chmod(0o755)
    package = repo / "node_modules" / "eslint"
    package.mkdir(parents=True)
    (package / "package.json").write_text(json.dumps({"version": version}) + "\n", encoding="utf-8")


def _script(payload: object, code: int) -> str:
    return _raw(json.dumps(payload), code)


def _raw(text: str, code: int) -> str:
    return (
        "#!/usr/bin/env python3\n"
        "import os\n"
        "import sys\n"
        "if not os.path.sameopenfile(0, os.open(os.devnull, os.O_RDONLY)):\n"
        "    sys.exit(9)\n"
        "if '--format' not in sys.argv or 'json' not in sys.argv:\n"
        "    sys.exit(9)\n"
        "if not os.path.exists(sys.argv[-1]):\n"
        "    sys.exit(9)\n"
        f"sys.stdout.write({text!r})\n"
        f"sys.exit({code})\n"
    )
