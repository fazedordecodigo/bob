from __future__ import annotations

import importlib
import importlib.metadata
import json
import os
import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from bob_quality.config import Config, SourceLanguage
from bob_quality.core import cognitive_verdict
from bob_quality.messages import Text, msg
from bob_quality.models import CognitiveFunction, GateResult
from bob_quality.npm_tools import installed_npm_version, node_missing_message, npm_prefix
from bob_quality.tools import ToolError
from bob_quality.waivers import load_waivers

__all__ = ["run_cognitive_gate"]

_Outcome = tuple[GateResult, list[CognitiveFunction], Literal[0], dict[str, str]]


@dataclass(frozen=True)
class _LanguageFunctions:
    functions: list[CognitiveFunction]
    versions: dict[str, str]


@dataclass(frozen=True)
class _LanguageMiss:
    reason: Text


def run_cognitive_gate(
    cwd: Path,
    config: Config,
    diff_lines: dict[str, set[int]],
) -> _Outcome:
    measured: list[_LanguageFunctions] = []
    misses: list[_LanguageMiss] = []
    for language in config.languages:
        outcome = _MEASURE[language](cwd, config)
        if isinstance(outcome, _LanguageMiss):
            misses.append(outcome)
            continue
        measured.append(outcome)
    if not measured:
        if not misses:
            result, found, code = cognitive_verdict([], config.max_cognitive, set(), diff_lines)
            return result, found, code, {}
        return GateResult("cognitive", "not_run", _miss_reason(misses)), [], 0, {}
    functions = [item for batch in measured for item in batch.functions]
    versions: dict[str, str] = {}
    for batch in measured:
        versions.update(batch.versions)
    waived = {item.id for item in load_waivers(cwd)}
    result, found, code = cognitive_verdict(
        functions, config.max_cognitive, waived, diff_lines
    )
    return result, found, code, versions


def _miss_reason(misses: list[_LanguageMiss]) -> Text:
    reason = misses[0].reason
    for miss in misses[1:]:
        reason = msg("probe.joined", first=reason, second=miss.reason)
    return reason


def _measure_python(cwd: Path, config: Config) -> _LanguageFunctions | _LanguageMiss:
    try:
        module = _load_complexipy()
    except ImportError:
        return _LanguageMiss(msg("cognitive.tool_missing", tool="complexipy"))
    try:
        functions = _python_functions(cwd, config, module)
        version = importlib.metadata.version("complexipy")
    except Exception as exc:
        return _LanguageMiss(msg("cognitive.tool_bad", tool="complexipy", detail=_detail(exc)))
    return _LanguageFunctions(functions, {"complexipy": version})


def _load_complexipy():
    return importlib.import_module("complexipy")


def _python_functions(cwd: Path, config: Config, module: object) -> list[CognitiveFunction]:
    found: list[CognitiveFunction] = []
    for path in _python_files(cwd, config):
        measure_file = getattr(module, "file_complexity")
        measured = measure_file(str(path), check_script=False, no_ignore=True)
        relative = _relative(cwd, _text(getattr(measured, "path", None), "path"))
        for item in _items(getattr(measured, "functions", None)):
            name, score, start, end = _function_fields(item)
            found.append(
                CognitiveFunction(
                    file=relative,
                    name=name,
                    start_line=start,
                    end_line=end,
                    score=score,
                    language="python",
                )
            )
    return found


def _python_files(cwd: Path, config: Config) -> list[Path]:
    found: list[Path] = []
    for root in config.include:
        base = cwd / root
        if base.is_file() and base.suffix == ".py" and not _excluded(base.relative_to(cwd), config):
            found.append(base)
            continue
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*.py")):
            if _excluded(path.relative_to(cwd), config):
                continue
            found.append(path)
    return found


def _excluded(relative: Path, config: Config) -> bool:
    return any(name in relative.parts for name in config.exclude)


def _function_fields(item: object) -> tuple[str, int, int, int]:
    name = getattr(item, "name", None)
    score = getattr(item, "complexity", None)
    start = getattr(item, "line_start", None)
    end = getattr(item, "line_end", None)
    if not isinstance(name, str) or name == "":
        raise ValueError("function is missing name, complexity, line_start, or line_end")
    if not _whole(score) or not _whole(start) or not _whole(end):
        raise ValueError("function is missing name, complexity, line_start, or line_end")
    return name, score, start, end


def _whole(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _items(value: object) -> list[object]:
    if value is None:
        raise ValueError("function is missing name, complexity, line_start, or line_end")
    if isinstance(value, list):
        return value
    return list(value)


def _text(value: object, label: str) -> str:
    if isinstance(value, str) and value != "":
        return value
    raise ValueError(f"function is missing {label}")


def _relative(cwd: Path, raw: str) -> str:
    path = Path(raw)
    if path.is_absolute():
        path = path.resolve().relative_to(cwd.resolve())
    text = path.as_posix()
    if text.startswith("./"):
        return text[2:]
    return text


def _detail(exc: BaseException) -> str:
    text = str(exc).strip().splitlines()
    line = text[0] if text else "failed"
    return line.replace("{", "(").replace("}", ")")


_Measure = Callable[[Path, Config], _LanguageFunctions | _LanguageMiss]


def _measure_typescript(cwd: Path, config: Config) -> _LanguageFunctions | _LanguageMiss:
    if node_missing_message() is not None:
        return _LanguageMiss(msg("cognitive.tool_missing", tool="node"))
    try:
        prefix = npm_prefix()
        versions = {
            "eslint": installed_npm_version(prefix, "eslint"),
            "eslint-plugin-sonarjs": installed_npm_version(prefix, "eslint-plugin-sonarjs"),
        }
    except ToolError:
        return _LanguageMiss(msg("cognitive.tool_missing", tool="eslint"))
    try:
        functions = _parse_payload(_run_eslint(cwd, config, prefix), cwd)
    except (OSError, ValueError) as exc:
        return _LanguageMiss(msg("cognitive.tool_bad", tool="eslint", detail=_detail(exc)))
    return _LanguageFunctions(functions, versions)


def _run_eslint(cwd: Path, config: Config, prefix: Path) -> str:
    script = Path(__file__).resolve().parent / "js" / "eslint_cognitive.mjs"
    payload = json.dumps(
        {
            "limit": config.max_cognitive,
            "cwd": str(cwd.resolve()),
            "include": list(config.include),
            "exclude": list(config.exclude),
        }
    )
    env = {key: value for key, value in os.environ.items() if not key.startswith("PYTEST_")}
    env["NODE_PATH"] = str(prefix / "node_modules")
    completed = subprocess.run(
        ["node", str(script)],
        cwd=cwd,
        input=payload,
        capture_output=True,
        text=True,
        env=env,
    )
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout).strip() or "eslint failed"
        raise ValueError(detail)
    return completed.stdout


def _parse_payload(raw: str, cwd: Path) -> list[CognitiveFunction]:
    payload = json.loads(raw)
    if not isinstance(payload, list):
        raise ValueError("unreadable cognitive payload")
    return [_domain_row(item, cwd) for item in payload]


def _domain_row(item: object, cwd: Path) -> CognitiveFunction:
    if not isinstance(item, dict):
        raise ValueError("unreadable cognitive payload")
    if "messages" in item or "filePath" in item:
        raise ValueError("eslint payload is not domain json")
    return CognitiveFunction(
        file=_relative(cwd, _required_text(item, "file")),
        name=_required_text(item, "name"),
        start_line=_required_int(item, "start_line"),
        end_line=_required_int(item, "end_line"),
        score=_required_int(item, "score"),
        language="typescript",
    )


def _required_text(item: dict[str, object], key: str) -> str:
    value = item.get(key)
    if isinstance(value, str) and value != "":
        return value
    raise ValueError(f"function is missing {key}")


def _required_int(item: dict[str, object], key: str) -> int:
    value = item.get(key)
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    raise ValueError(f"function is missing {key}")


_MEASURE: dict[SourceLanguage, _Measure] = {
    "python": _measure_python,
    "typescript": _measure_typescript,
}
