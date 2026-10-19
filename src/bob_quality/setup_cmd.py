"""bob setup: passos do CT3, resumo e código de saída."""

from __future__ import annotations

import importlib.metadata
import platform
import re
import shutil
import subprocess
import sys
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from bob_quality import doctor
from bob_quality import install_skills
from bob_quality import npm_tools
from bob_quality import user_dirs
from bob_quality.install_skills import SkillsResult, SourceError
from bob_quality.messages import Language, Text, msg, reason, render, t
from bob_quality.npm_tools import NodeRange, PinSourceError
from bob_quality.tools import ToolError
from bob_quality.user_dirs import BobHome

Status = Literal["installed", "unchanged", "preserved", "failed"]


@dataclass(frozen=True)
class SetupContext:
    project: Path
    home: BobHome
    lang: Language
    version: str


@dataclass(frozen=True)
class StepResult:
    status: Status
    installed: tuple[Text, ...] = ()
    preserved: tuple[Text, ...] = ()
    warnings: tuple[Text, ...] = ()
    error: Text | None = None


Step = Callable[[SetupContext], StepResult]


def step_projeto(ctx: SetupContext) -> StepResult:
    if shutil.which("git") is None:
        return StepResult("failed", error=msg("setup.git_missing"))
    try:
        completed = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=ctx.project,
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return _not_git_root(ctx)
    if completed.returncode != 0:
        return _not_git_root(ctx)
    top = Path(completed.stdout.strip()).resolve()
    if top != ctx.project:
        return _not_git_root(ctx)
    return StepResult("unchanged")


def step_runtimes(ctx: SetupContext) -> StepResult:
    try:
        floor = _python_floor()
    except ValueError as exc:
        return StepResult(
            "failed",
            error=msg("setup.python_floor_bad", value=str(exc)),
        )
    if sys.version_info[:2] < floor:
        return StepResult(
            "failed",
            error=msg(
                "setup.python_old",
                found=platform.python_version(),
                floor=f"{floor[0]}.{floor[1]}",
            ),
        )
    try:
        node = npm_tools.node_range()
    except PinSourceError as exc:
        return _failed_reason("runtimes", exc)
    found = _node_version_text()
    if found is None:
        return StepResult("failed", error=_node_message("setup.node_missing", node))
    if not _node_ok(found):
        return StepResult(
            "failed",
            error=_node_message("setup.node_out", node, found),
        )
    return StepResult("unchanged")


def step_npm(ctx: SetupContext) -> StepResult:
    try:
        pins = npm_tools.pinned_npm_versions()
    except PinSourceError as exc:
        return _failed_reason("npm", exc)
    if _npm_ready(pins):
        return StepResult("unchanged")
    code = npm_tools.install_npm_dependencies(ctx.lang)
    if code != 0:
        return StepResult("failed", error=msg("setup.npm_failed"))
    return StepResult("installed", installed=(msg("setup.item_npm"),))


def step_skills(ctx: SetupContext) -> StepResult:
    try:
        result = install_skills.install_project_skills(ctx.project, ctx.version)
    except SourceError as exc:
        return StepResult(
            "failed",
            error=msg("setup.skills_source", detail=str(exc)),
        )
    except OSError as exc:
        return StepResult("failed", error=_skills_write_error(exc))
    return _skills_outcome(ctx, result)


STEPS: tuple[tuple[str, Step], ...] = (
    ("projeto", step_projeto),
    ("runtimes", step_runtimes),
    ("npm", step_npm),
    ("skills", step_skills),
)


def run_setup(project: Path, lang: Language) -> int:
    """Roda os passos do CT3 em ordem, o bob doctor e o resumo."""
    try:
        ctx = SetupContext(
            project=project.resolve(),
            home=user_dirs.bob_home(),
            lang=lang,
            version=importlib.metadata.version("bob-quality"),
        )
    except ValueError as exc:
        _fail(lang, msg("setup.bob_home_relative", value=str(exc)), (), (), ())
        return 4
    return _run(ctx)


def _node_version_text() -> str | None:
    node = shutil.which("node")
    if node is None:
        return None
    try:
        completed = subprocess.run(
            [node, "--version"],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if completed.returncode != 0:
        return None
    return completed.stdout.strip()


def _python_floor() -> tuple[int, int]:
    value = importlib.metadata.metadata("bob-quality")["Requires-Python"]
    match = re.fullmatch(r">=(\d+)\.(\d+)", value)
    if match is None:
        raise ValueError(value)
    return int(match.group(1)), int(match.group(2))


def _run(ctx: SetupContext) -> int:
    installed: list[Text] = []
    preserved: list[Text] = []
    warnings: list[Text] = []
    for step_id, step in STEPS:
        result = _invoke(step_id, step, ctx)
        if result.status == "failed":
            _fail(ctx.lang, result.error, installed, preserved, warnings)
            return 4
        _announce(ctx.lang, step_id, result.warnings)
        installed.extend(result.installed)
        preserved.extend(result.preserved)
        warnings.extend(result.warnings)
    code = doctor.run_doctor(install=False, lang=ctx.lang)
    _summary(ctx.lang, installed, preserved, warnings, str(code))
    if code == 0:
        return 0
    return 4


def _invoke(step_id: str, step: Step, ctx: SetupContext) -> StepResult:
    try:
        return step(ctx)
    except Exception as exc:
        return StepResult(
            "failed",
            error=msg(
                "setup.internal_error",
                step=step_id,
                kind=type(exc).__name__,
            ),
        )


def _announce(lang: Language, step_id: str, warnings: Sequence[Text]) -> None:
    print(t(lang, "setup.step_ok", step=step_id))
    for warning in warnings:
        print(
            t(
                lang,
                "setup.warning_line",
                step=step_id,
                text=render(warning, lang),
            )
        )


def _fail(
    lang: Language,
    error: Text | None,
    installed: Sequence[Text],
    preserved: Sequence[Text],
    warnings: Sequence[Text],
) -> None:
    print(t(lang, "setup.error", reason=render(error, lang)), file=sys.stderr)
    _summary(
        lang,
        installed,
        preserved,
        warnings,
        t(lang, "setup.doctor_not_run"),
    )


def _summary(
    lang: Language,
    installed: Sequence[Text],
    preserved: Sequence[Text],
    warnings: Sequence[Text],
    doctor_code: str,
) -> None:
    print(t(lang, "setup.summary"))
    print(t(lang, "setup.installed", items=_items(lang, installed)))
    for item in preserved:
        print(t(lang, "setup.preserved", item=render(item, lang)))
    for warning in warnings:
        print(t(lang, "setup.warnings", text=render(warning, lang)))
    print(t(lang, "setup.doctor", code=doctor_code))


def _items(lang: Language, installed: Sequence[Text]) -> str:
    if not installed:
        return t(lang, "setup.nothing")
    return ", ".join(render(item, lang) for item in installed)


def _not_git_root(ctx: SetupContext) -> StepResult:
    return StepResult("failed", error=msg("setup.not_git_root", path=ctx.project))


def _failed_reason(step: str, exc: BaseException) -> StepResult:
    return StepResult(
        "failed",
        error=msg("setup.step_reason", step=step, reason=reason(exc)),
    )


def _node_ok(found: str) -> bool:
    match = re.fullmatch(r"v(\d+\.\d+\.\d+)", found)
    if match is None:
        return False
    return doctor.node_admits(doctor.node_pin(), match.group(1))


def _node_message(key: str, node: NodeRange, found: str | None = None) -> Text:
    floor = node.floor
    params: dict[str, object] = {
        "range": str(node),
        "floor": ".".join(str(part) for part in floor),
        "major": str(floor[0]),
    }
    if found is not None:
        params["found"] = found
    return msg(key, **params)


def _npm_ready(pins: dict[str, str]) -> bool:
    try:
        prefix = npm_tools.npm_prefix()
    except ToolError:
        return False
    for name, version in pins.items():
        if not _npm_version_is(prefix, name, version):
            return False
    return True


def _npm_version_is(prefix: Path, name: str, version: str) -> bool:
    try:
        found = npm_tools.installed_npm_version(prefix, name)
    except ToolError:
        return False
    return found == version


def _skills_write_error(exc: OSError) -> Text:
    if exc.filename:
        path = exc.filename
    else:
        path = ".agents/skills"
    return msg(
        "setup.skills_write",
        path=path,
        detail=exc.strerror or type(exc).__name__,
    )


def _skills_outcome(ctx: SetupContext, result: SkillsResult) -> StepResult:
    preserved = tuple(_preserved_item(ctx, path, result) for path in result.preserved)
    warnings = _skill_warnings(ctx, result)
    if not result.installed:
        return StepResult("unchanged", preserved=preserved, warnings=warnings)
    names = ", ".join(result.installed)
    return StepResult(
        "installed",
        installed=(msg("setup.item_skills", names=names),),
        preserved=preserved,
        warnings=warnings,
    )


def _skill_warnings(ctx: SetupContext, result: SkillsResult) -> tuple[Text, ...]:
    unmarked = tuple(
        msg("setup.warn_no_marker", path=_relative(ctx, path)) for path in result.unmarked
    )
    copies = tuple(
        msg("setup.warn_duplicate", path=_relative(ctx, path)) for path in result.duplicates
    )
    return unmarked + copies


def _preserved_item(ctx: SetupContext, path: Path, result: SkillsResult) -> Text:
    relative = _relative(ctx, path)
    if path in result.unmarked:
        return msg("setup.preserved_no_marker", path=relative)
    if path.is_symlink():
        return msg("setup.preserved_symlink", path=relative)
    if path.is_file():
        return msg("setup.preserved_file", path=relative)
    return msg("setup.preserved_foreign", path=relative)


def _relative(ctx: SetupContext, path: Path) -> str:
    return path.relative_to(ctx.project).as_posix()
