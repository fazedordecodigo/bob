"""Gate de complexidade cognitiva. A medição fica aqui; o veredito fica no núcleo."""

from __future__ import annotations

import importlib
import importlib.metadata
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from bob_quality.config import Config, SourceLanguage
from bob_quality.core import cognitive_verdict
from bob_quality.messages import Text, msg
from bob_quality.models import CognitiveFunction, GateResult
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
    """Mede cada idioma configurado e chama o veredito uma vez.

    Idioma que não mediu fica de fora. Se todos falham, o status é not_run
    e o exit é 0.
    """
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
    # A top-level import would make every bob check fail when the package is absent.
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

_MEASURE: dict[SourceLanguage, _Measure] = {
    "python": _measure_python,
}
