"""Comportamento do c8 que a suíte da CLI não alcança no processo do mutmut."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from bob_quality.adapters.istanbul import parse_coverage_final
from bob_quality.npm_tools import NODE_MISSING, run_vitest_under_c8
from bob_quality.tools import ToolError

FIXTURE_TS = Path(__file__).parent / "fixtures" / "ts_app"
_EXCLUDE = ["tests", "node_modules", "dist"]


def _copy_fixture(dest: Path) -> Path:
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(FIXTURE_TS, dest)
    return dest


def _paths(payload: dict[str, object]) -> list[str]:
    return [path.replace("\\", "/") for path in payload]


def test_run_vitest_under_c8_names_the_missing_node(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    bindir = tmp_path / "bin"
    bindir.mkdir()
    monkeypatch.setenv("PATH", str(bindir))

    with pytest.raises(ToolError) as caught:
        run_vitest_under_c8(FIXTURE_TS, ["src"], tmp_path / "coverage", _EXCLUDE)

    assert str(caught.value) == NODE_MISSING


def test_c8_creates_a_nested_reports_directory_and_can_run_again(tmp_path: Path) -> None:
    reports = tmp_path / "missing-parent" / "coverage"

    first = run_vitest_under_c8(FIXTURE_TS, ["src"], reports, _EXCLUDE)
    second = run_vitest_under_c8(FIXTURE_TS, ["src"], reports, _EXCLUDE)

    assert first == 0
    assert second == 0
    assert (reports / "coverage-final.json").is_file()


def test_c8_records_an_untested_file_and_skips_an_excluded_one(tmp_path: Path) -> None:
    repo = _copy_fixture(tmp_path / "repo")
    (repo / "src" / "lonely.ts").write_text("export function lonely(): number { return 1 }\n")
    (repo / "vendor").mkdir()
    (repo / "vendor" / "used.ts").write_text("export function used(): number { return 2 }\n")
    test = repo / "tests" / "safe.test.ts"
    test.write_text(test.read_text().replace(
        'import { add } from "../src/safe";',
        'import { add } from "../src/safe";\nimport { used } from "../vendor/used";',
    ).replace(
        "expect(add(1, 2)).toBe(3);",
        "expect(add(1, 2)).toBe(3);\n  expect(used()).toBe(2);",
    ))
    reports = tmp_path / "coverage"

    code = run_vitest_under_c8(repo, ["src", "vendor"], reports, ["vendor", "tests"])
    paths = _paths(parse_coverage_final((reports / "coverage-final.json").read_text()))

    assert code == 0
    assert any(path.endswith("src/lonely.ts") for path in paths)
    assert any(path.endswith("src/safe.ts") for path in paths)
    assert not any(path.endswith("vendor/used.ts") for path in paths)
    assert not any(path.endswith("tests/safe.test.ts") for path in paths)


def test_empty_include_measures_src_and_not_a_sibling_folder(tmp_path: Path) -> None:
    repo = _copy_fixture(tmp_path / "repo")
    (repo / "extra").mkdir()
    (repo / "extra" / "lonely.ts").write_text("export function lonely(): number { return 1 }\n")
    reports = tmp_path / "coverage"

    code = run_vitest_under_c8(repo, [], reports, _EXCLUDE)
    paths = _paths(parse_coverage_final((reports / "coverage-final.json").read_text()))

    assert code == 0
    assert any(path.endswith("src/safe.ts") for path in paths)
    assert not any("extra/lonely.ts" in path for path in paths)


def test_pytest_env_does_not_leak_into_vitest(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PYTEST_CURRENT_TEST", "tests/test_c8_runner.py::leak")
    repo = _copy_fixture(tmp_path / "repo")
    (repo / "vitest.config.mjs").write_text(
        "\n".join(
            [
                "if (process.env.PYTEST_CURRENT_TEST) throw new Error('PYTEST_LEAK');",
                "export default { test: { include: ['tests/safe.test.ts'] } };",
                "",
            ]
        )
    )
    reports = tmp_path / "coverage"

    code = run_vitest_under_c8(repo, ["src"], reports, _EXCLUDE)

    assert code == 0


def test_mjs_config_does_not_receive_the_strip_types_flag(tmp_path: Path) -> None:
    repo = _copy_fixture(tmp_path / "repo")
    (repo / "vitest.config.mjs").write_text(
        "\n".join(
            [
                "if ((process.env.NODE_OPTIONS || '').includes('--experimental-strip-types')) {",
                "  throw new Error('STRIP_FLAG_ON_MJS');",
                "}",
                "export default { test: { include: ['tests/safe.test.ts'] } };",
                "",
            ]
        )
    )
    reports = tmp_path / "coverage"

    code = run_vitest_under_c8(repo, ["src"], reports, _EXCLUDE)

    assert code == 0


def test_node_options_without_the_strip_flag_gain_it_and_keep_the_rest(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("NODE_OPTIONS", "--no-warnings")
    repo = _copy_fixture(tmp_path / "repo")
    (repo / "vitest.config.mjs").unlink()
    (repo / "vitest.config.ts").write_text(
        "\n".join(
            [
                "const options = process.env.NODE_OPTIONS || '';",
                "if (!options.includes('--no-warnings')) throw new Error('LOST_NODE_OPTIONS');",
                "if (!options.includes('--experimental-strip-types')) throw new Error('NO_STRIP_FLAG');",
                "export default { test: { include: ['tests/safe.test.ts'] } };",
                "",
            ]
        )
    )
    reports = tmp_path / "coverage"

    code = run_vitest_under_c8(repo, ["src"], reports, _EXCLUDE)

    assert code == 0


def test_existing_node_options_are_kept_when_loading_typescript_config(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("NODE_OPTIONS", "--no-warnings --experimental-strip-types")
    repo = _copy_fixture(tmp_path / "repo")
    (repo / "vitest.config.mjs").unlink()
    (repo / "vitest.config.ts").write_text(
        "\n".join(
            [
                "const options = process.env.NODE_OPTIONS || '';",
                "const flags = options.split('--experimental-strip-types').length - 1;",
                "if (!options.includes('--no-warnings')) throw new Error('LOST_NODE_OPTIONS');",
                "if (flags !== 1) throw new Error('STRIP_FLAG_COUNT_' + flags);",
                "export default { test: { include: ['tests/safe.test.ts'] } };",
                "",
            ]
        )
    )
    reports = tmp_path / "coverage"

    code = run_vitest_under_c8(repo, ["src"], reports, _EXCLUDE)

    assert code == 0


def test_user_vitest_config_decides_which_tests_run(tmp_path: Path) -> None:
    repo = _copy_fixture(tmp_path / "repo")
    (repo / "tests" / "boom.test.ts").write_text(
        "\n".join(
            [
                'import { expect, test } from "vitest";',
                'test("boom", () => { expect(1).toBe(2) })',
                "",
            ]
        )
    )
    (repo / "vitest.config.mjs").write_text(
        "\n".join(
            [
                "export default {",
                "  test: { include: ['tests/safe.test.ts'] },",
                "}",
                "",
            ]
        )
    )
    reports = tmp_path / "coverage"

    code = run_vitest_under_c8(repo, ["src"], reports, _EXCLUDE)

    assert code == 0
    assert (reports / "coverage-final.json").is_file()


def test_failed_vitest_keeps_the_coverage_file_and_returns_its_code(tmp_path: Path) -> None:
    repo = _copy_fixture(tmp_path / "repo")
    (repo / "vitest.config.mjs").write_text('throw new Error("CONFIG_BOOM")\n')
    reports = tmp_path / "coverage"

    code = run_vitest_under_c8(repo, ["src"], reports, _EXCLUDE)

    assert code != 0
    assert (reports / "coverage-final.json").is_file()


def _loads_typescript_config(tmp_path: Path, name: str) -> None:
    repo = _copy_fixture(tmp_path / "repo")
    (repo / "vitest.config.mjs").unlink()
    (repo / name).write_text(
        "\n".join(
            [
                "export default {",
                "  test: { include: ['tests/safe.test.ts'] },",
                "}",
                "",
            ]
        )
    )
    reports = tmp_path / "coverage"

    code = run_vitest_under_c8(repo, ["src"], reports, _EXCLUDE)
    paths = _paths(parse_coverage_final((reports / "coverage-final.json").read_text()))

    assert code == 0
    assert any(path.endswith("src/safe.ts") for path in paths)


def test_vitest_config_ts_is_loaded(tmp_path: Path) -> None:
    _loads_typescript_config(tmp_path, "vitest.config.ts")


def test_vitest_config_mts_is_loaded(tmp_path: Path) -> None:
    _loads_typescript_config(tmp_path, "vitest.config.mts")


def test_include_outside_src_is_measured(tmp_path: Path) -> None:
    repo = _copy_fixture(tmp_path / "repo")
    (repo / "lib").mkdir()
    (repo / "lib" / "kept.ts").write_text("export function kept(): number { return 4 }\n")
    test = repo / "tests" / "safe.test.ts"
    test.write_text(
        test.read_text()
        .replace(
            'import { add } from "../src/safe";',
            'import { add } from "../src/safe";\nimport { kept } from "../lib/kept";',
        )
        .replace(
            "expect(add(1, 2)).toBe(3);",
            "expect(add(1, 2)).toBe(3);\n  expect(kept()).toBe(4);",
        )
    )
    reports = tmp_path / "coverage"

    code = run_vitest_under_c8(repo, ["lib"], reports, _EXCLUDE)
    paths = _paths(parse_coverage_final((reports / "coverage-final.json").read_text()))

    assert code == 0
    assert any(path.endswith("lib/kept.ts") for path in paths)


def test_c8_failure_without_output_uses_the_fallback_message(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fake_run(args: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(args, 1, stdout="", stderr="")

    monkeypatch.setattr("bob_quality.npm_tools.subprocess.run", fake_run)

    with pytest.raises(ToolError) as caught:
        run_vitest_under_c8(FIXTURE_TS, ["src"], tmp_path / "coverage", _EXCLUDE)

    assert str(caught.value) == "c8/vitest falhou"


def _assert_captured_pinned_call(args: list[str], kwargs: dict[str, object]) -> None:
    assert kwargs.get("capture_output") is True
    assert kwargs.get("text") is True
    assert kwargs.get("stdin") is subprocess.DEVNULL
    prefix = Path(args[args.index("--prefix") + 1])
    package = json.loads((prefix / "package.json").read_text())
    assert package["name"] == "bob-quality-tools"
    root = Path(args[args.index("--root") + 1])
    assert (root / "src").is_dir()


def test_c8_failure_without_a_coverage_file_reports_stderr(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fake_run(args: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        _assert_captured_pinned_call(args, kwargs)
        return subprocess.CompletedProcess(args, 1, stdout="", stderr="C8_STDERR_UNIQUE")

    monkeypatch.setattr("bob_quality.npm_tools.subprocess.run", fake_run)

    with pytest.raises(ToolError) as caught:
        run_vitest_under_c8(FIXTURE_TS, ["src"], tmp_path / "coverage", _EXCLUDE)

    assert "C8_STDERR_UNIQUE" in str(caught.value)


def test_c8_failure_without_stderr_reports_stdout(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fake_run(args: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        _assert_captured_pinned_call(args, kwargs)
        return subprocess.CompletedProcess(args, 1, stdout="C8_STDOUT_UNIQUE", stderr="")

    monkeypatch.setattr("bob_quality.npm_tools.subprocess.run", fake_run)

    with pytest.raises(ToolError) as caught:
        run_vitest_under_c8(FIXTURE_TS, ["src"], tmp_path / "coverage", _EXCLUDE)

    assert str(caught.value) == "C8_STDOUT_UNIQUE"
