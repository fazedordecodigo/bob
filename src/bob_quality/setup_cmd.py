"""bob setup: passos do CT3, resumo e código de saída."""

from __future__ import annotations

import importlib.metadata
import os
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
from bob_quality import gitleaks
from bob_quality import hook_install
from bob_quality import init_config
from bob_quality import install_skills
from bob_quality import npm_tools
from bob_quality import user_dirs
from bob_quality.config import ConfigError
from bob_quality.gitleaks import GitleaksError
from bob_quality.hook_install import HookPathError, HookResult
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

_FAILED: Status = "failed"
_INSTALLED: Status = "installed"
_UNCHANGED: Status = "unchanged"
_GIT = "git"
_GIT_TOPLEVEL = ("git", "rev-parse", "--show-toplevel")
_NODE = "node"
_NODE_FLAG = "--version"
_NODE_TIMEOUT = 30
_DOCTOR_INSTALL = False
_PKG = "bob-quality"
_PY_REQUIRES = "Requires-Python"
_PY_FLOOR_RE = r">=(\d+)\.(\d+)"
_NODE_RE = r"v(\d+\.\d+\.\d+)"
_SKILLS_FALLBACK = ".agents/skills"
_COMMA = ", "
_DOT = "."
_RUNTIMES = "runtimes"
_NPM = "npm"
_RANGE = "range"
_FLOOR = "floor"
_MAJOR = "major"
_FOUND = "found"
_STEP_OK = "setup.step_ok"
_WARNING_LINE = "setup.warning_line"
_ERROR = "setup.error"
_SUMMARY = "setup.summary"
_INSTALLED_LINE = "setup.installed"
_NOTHING = "setup.nothing"
_PRESERVED_LINE = "setup.preserved"
_WARNINGS_LINE = "setup.warnings"
_DOCTOR_LINE = "setup.doctor"
_DOCTOR_NOT_RUN = "setup.doctor_not_run"
_PROFILE_ENV = "BOB_INSTALL_PROFILE"
_PROFILE_LINE = "setup.profile"
_PROFILE_ON_PATH = "already-on-path"
_PROFILE_ON_PATH_KEY = "setup.profile_on_path"
_PROFILE_ADDED_KEY = "setup.profile_added"
_PROFILE_KINDS = {"already-marked": "setup.profile_marked", "failed": "setup.profile_failed"}
_INTERNAL = "setup.internal_error"
_STEP_REASON = "setup.step_reason"
_GIT_MISSING = "setup.git_missing"
_NOT_GIT_ROOT = "setup.not_git_root"
_BOB_HOME_RELATIVE = "setup.bob_home_relative"
_PYTHON_FLOOR_BAD = "setup.python_floor_bad"
_PYTHON_OLD = "setup.python_old"
_NODE_MISSING = "setup.node_missing"
_NODE_OUT = "setup.node_out"
_NPM_FAILED = "setup.npm_failed"
_SKILLS_SOURCE = "setup.skills_source"
_SKILLS_WRITE = "setup.skills_write"
_ITEM_NPM = "setup.item_npm"
_GITLEAKS = "gitleaks"
_BOB_YAML = "bob.yaml"
_ITEM_GITLEAKS = "setup.item_gitleaks"
_ITEM_SKILLS = "setup.item_skills"
_NO_MARKER = "setup.preserved_no_marker"
_SYMLINK = "setup.preserved_symlink"
_FILE = "setup.preserved_file"
_FOREIGN = "setup.preserved_foreign"
_WARN_NO_MARKER = "setup.warn_no_marker"
_WARN_DUPLICATE = "setup.warn_duplicate"
_ITEM_BOB_YAML = "setup.item_bob_yaml"
_PRESERVED_BOB_YAML = "setup.preserved_bob_yaml"
_PRESERVED_WAIVERS = "setup.preserved_waivers"
_WARN_NO_CODE = "setup.warn_no_code"
_BOB_YAML_INVALID = "setup.bob_yaml_invalid"
_BOB_YAML_WRITE = "setup.bob_yaml_write"
_HOOK = "hook"
_ITEM_HOOK = "setup.item_hook"
_ITEM_HOOK_UPDATED = "setup.item_hook_updated"
_PRESERVED_HOOK = "setup.preserved_hook"
_PRESERVED_HOOKSPATH = "setup.preserved_hookspath"
_WARN_HOOK_FOREIGN = "setup.warn_hook_foreign"
_WARN_HOOKSPATH = "setup.warn_hookspath"
_HOOK_BAD_PATH = "setup.hook_bad_path"
_HOOK_WRITE = "setup.hook_write"
_HOOK_FILE = ".git/hooks/pre-push"


def step_projeto(ctx: SetupContext) -> StepResult:
    if shutil.which(_GIT) is None:
        return StepResult(_FAILED, error=msg(_GIT_MISSING))
    try:
        completed = subprocess.run(
            list(_GIT_TOPLEVEL),
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
    return StepResult(_UNCHANGED)


def step_runtimes(ctx: SetupContext) -> StepResult:
    try:
        floor = _python_floor()
    except ValueError as exc:
        return StepResult(_FAILED, error=msg(_PYTHON_FLOOR_BAD, value=str(exc)))
    found_py = (sys.version_info[0], sys.version_info[1])
    if found_py < floor:
        dotted = _DOT.join((str(floor[0]), str(floor[1])))
        return StepResult(
            _FAILED,
            error=msg(
                _PYTHON_OLD,
                found=platform.python_version(),
                floor=dotted,
            ),
        )
    try:
        node = npm_tools.node_range()
    except PinSourceError as exc:
        return _failed_reason(_RUNTIMES, exc)
    found = _node_version_text()
    if found is None:
        return StepResult(_FAILED, error=_node_message(_NODE_MISSING, node))
    if not _node_ok(found):
        return StepResult(_FAILED, error=_node_message(_NODE_OUT, node, found))
    return StepResult(_UNCHANGED)


def step_npm(ctx: SetupContext) -> StepResult:
    try:
        pins = npm_tools.pinned_npm_versions()
    except PinSourceError as exc:
        return _failed_reason(_NPM, exc)
    if _npm_ready(pins):
        return StepResult(_UNCHANGED)
    code = npm_tools.install_npm_dependencies(ctx.lang)
    if code != 0:
        return StepResult(_FAILED, error=msg(_NPM_FAILED))
    return StepResult(_INSTALLED, installed=(msg(_ITEM_NPM),))


def step_gitleaks(ctx: SetupContext) -> StepResult:
    """Passo 4 do CT3: gitleaks 8.30.1 em BOB_HOME (CT9)."""
    if gitleaks.installed_version(ctx.home) == gitleaks.VERSION:
        return StepResult(_UNCHANGED)
    try:
        gitleaks.ensure_gitleaks(ctx.home)
    except GitleaksError as exc:
        return StepResult(_FAILED, error=reason(exc))
    return StepResult(
        _INSTALLED,
        installed=(msg(_ITEM_GITLEAKS, version=gitleaks.VERSION),),
    )


def step_skills(ctx: SetupContext) -> StepResult:
    try:
        result = install_skills.install_project_skills(ctx.project, ctx.version)
    except SourceError as exc:
        return StepResult(_FAILED, error=msg(_SKILLS_SOURCE, detail=str(exc)))
    except OSError as exc:
        return StepResult(_FAILED, error=_skills_write_error(exc))
    return _skills_outcome(ctx, result)


def step_bob_yaml(ctx: SetupContext) -> StepResult:
    """Passo 6 do CT3: bob.yaml do projeto (CT7) e waivers preservados."""
    waivers = _waivers_kept(ctx)
    try:
        created = init_config.write_default_config(ctx.project)
    except ConfigError as exc:
        return StepResult(_FAILED, error=msg(_BOB_YAML_INVALID, detail=reason(exc)))
    except ToolError as exc:
        return _failed_reason(_BOB_YAML, exc)
    except OSError as exc:
        return _bob_yaml_write_failure(exc)
    return _config_result(created.state, waivers)


def step_hook(ctx: SetupContext) -> StepResult:
    """Passo 7 do CT3: hook pre-push do bob (CT10)."""
    bob = ctx.home.bin_bob
    try:
        result = hook_install.install_hook(ctx.project, bob)
    except HookPathError:
        return StepResult(_FAILED, error=msg(_HOOK_BAD_PATH, path=str(bob)))
    except ToolError as exc:
        return _failed_reason(_HOOK, exc)
    except OSError as exc:
        return StepResult(
            _FAILED,
            error=msg(
                _HOOK_WRITE,
                path=exc.filename or _HOOK_FILE,
                detail=exc.strerror or type(exc).__name__,
            ),
        )
    return _hook_result(ctx, result)


STEPS: tuple[tuple[str, Step], ...] = (
    ("projeto", step_projeto),
    ("runtimes", step_runtimes),
    ("npm", step_npm),
    (_GITLEAKS, step_gitleaks),
    ("skills", step_skills),
    (_BOB_YAML, step_bob_yaml),
    (_HOOK, step_hook),
)


def run_setup(project: Path, lang: Language) -> int:
    """Roda os passos do CT3 em ordem, o bob doctor e o resumo."""
    try:
        ctx = SetupContext(
            project=project.resolve(),
            home=user_dirs.bob_home(),
            lang=lang,
            version=importlib.metadata.version(_PKG),
        )
    except ValueError as exc:
        _fail(lang, msg(_BOB_HOME_RELATIVE, value=str(exc)), (), (), ())
        return 4
    return _run(ctx)


def _node_version_text() -> str | None:
    node = shutil.which(_NODE)
    if node is None:
        return None
    try:
        completed = subprocess.run(
            [node, _NODE_FLAG],
            capture_output=True,
            text=True,
            timeout=_NODE_TIMEOUT,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if completed.returncode != 0:
        return None
    return completed.stdout.strip()


def _python_floor() -> tuple[int, int]:
    value = importlib.metadata.metadata(_PKG)[_PY_REQUIRES]
    match = re.fullmatch(_PY_FLOOR_RE, value)
    if match is None:
        raise ValueError(value)
    return int(match.group(1)), int(match.group(2))


def _run(ctx: SetupContext) -> int:
    installed: list[Text] = []
    preserved: list[Text] = []
    warnings: list[Text] = []
    for step_id, step in STEPS:
        result = _invoke(step_id, step, ctx)
        if result.status == _FAILED:
            _fail(ctx.lang, result.error, installed, preserved, warnings)
            return 4
        _announce(ctx.lang, step_id, result.warnings)
        installed.extend(result.installed)
        preserved.extend(result.preserved)
        warnings.extend(result.warnings)
    code = doctor.run_doctor(install=_DOCTOR_INSTALL, lang=ctx.lang)
    _summary(ctx.lang, installed, preserved, warnings, str(code))
    if code == 0:
        return 0
    return 4


def _invoke(step_id: str, step: Step, ctx: SetupContext) -> StepResult:
    try:
        return step(ctx)
    except Exception as exc:
        return StepResult(
            _FAILED,
            error=msg(_INTERNAL, step=step_id, kind=type(exc).__name__),
        )


def _announce(lang: Language, step_id: str, warnings: Sequence[Text]) -> None:
    print(t(lang, _STEP_OK, step=step_id))
    for warning in warnings:
        print(
            t(
                lang,
                _WARNING_LINE,
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
    print(t(lang, _ERROR, reason=render(error, lang)), file=sys.stderr)
    _summary(lang, installed, preserved, warnings, t(lang, _DOCTOR_NOT_RUN))


def _profile_text(value: str | None) -> Text | None:
    if value is None:
        return None
    if value == _PROFILE_ON_PATH:
        return msg(_PROFILE_ON_PATH_KEY)
    head, _sep, rest = value.partition(":")
    kind = _PROFILE_KINDS.get(head)
    if kind is not None:
        if Path(rest).is_absolute():
            return msg(kind, path=rest)
        return None
    if Path(value).is_absolute():
        return msg(_PROFILE_ADDED_KEY, path=value)
    return None


def _summary(
    lang: Language,
    installed: Sequence[Text],
    preserved: Sequence[Text],
    warnings: Sequence[Text],
    doctor_code: str,
) -> None:
    print(t(lang, _SUMMARY))
    print(t(lang, _INSTALLED_LINE, items=_items(lang, installed)))
    for item in preserved:
        print(t(lang, _PRESERVED_LINE, item=render(item, lang)))
    for warning in warnings:
        print(t(lang, _WARNINGS_LINE, text=render(warning, lang)))
    profile = _profile_text(os.environ.get(_PROFILE_ENV))
    if profile is not None:
        print(t(lang, _PROFILE_LINE, text=profile))
    print(t(lang, _DOCTOR_LINE, code=doctor_code))


def _items(lang: Language, installed: Sequence[Text]) -> str:
    rendered = [render(item, lang) for item in installed]
    if not rendered:
        return t(lang, _NOTHING)
    return _COMMA.join(rendered)


def _not_git_root(ctx: SetupContext) -> StepResult:
    return StepResult(_FAILED, error=msg(_NOT_GIT_ROOT, path=ctx.project))


def _failed_reason(step: str, exc: BaseException) -> StepResult:
    return StepResult(_FAILED, error=msg(_STEP_REASON, step=step, reason=reason(exc)))


def _node_ok(found: str) -> bool:
    match = re.fullmatch(_NODE_RE, found)
    if match is None:
        return False
    return doctor.node_admits(doctor.node_pin(), match.group(1))


def _node_message(key: str, node: NodeRange, found: str | None = None) -> Text:
    floor = node.floor
    params: dict[str, object] = {
        _RANGE: str(node),
        _FLOOR: _DOT.join(str(part) for part in floor),
        _MAJOR: str(floor[0]),
    }
    if found is not None:
        params[_FOUND] = found
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
        path = _SKILLS_FALLBACK
    return msg(_SKILLS_WRITE, path=path, detail=exc.strerror or type(exc).__name__)


def _skills_outcome(ctx: SetupContext, result: SkillsResult) -> StepResult:
    preserved = tuple(_preserved_item(ctx, path, result) for path in result.preserved)
    warnings = _skill_warnings(ctx, result)
    if not result.installed:
        return StepResult(_UNCHANGED, preserved=preserved, warnings=warnings)
    names = _COMMA.join(result.installed)
    return StepResult(
        _INSTALLED,
        installed=(msg(_ITEM_SKILLS, names=names),),
        preserved=preserved,
        warnings=warnings,
    )


def _skill_warnings(ctx: SetupContext, result: SkillsResult) -> tuple[Text, ...]:
    unmarked = tuple(
        msg(_WARN_NO_MARKER, path=_relative(ctx, path)) for path in result.unmarked
    )
    copies = tuple(
        msg(_WARN_DUPLICATE, path=_relative(ctx, path)) for path in result.duplicates
    )
    return unmarked + copies


def _preserved_item(ctx: SetupContext, path: Path, result: SkillsResult) -> Text:
    relative = _relative(ctx, path)
    if path in result.unmarked:
        return msg(_NO_MARKER, path=relative)
    if path.is_symlink():
        return msg(_SYMLINK, path=relative)
    if path.is_file():
        return msg(_FILE, path=relative)
    return msg(_FOREIGN, path=relative)


def _relative(ctx: SetupContext, path: Path) -> str:
    return path.relative_to(ctx.project).as_posix()


def _waivers_kept(ctx: SetupContext) -> tuple[Text, ...]:
    path = ctx.project / ".bob" / "waivers.yaml"
    if path.exists() or path.is_symlink():
        return (msg(_PRESERVED_WAIVERS),)
    return ()


def _bob_yaml_write_failure(exc: OSError) -> StepResult:
    detail = exc.strerror or type(exc).__name__
    return StepResult(_FAILED, error=msg(_BOB_YAML_WRITE, detail=detail))


def _shown(ctx: SetupContext, path: Path) -> str:
    if path.is_relative_to(ctx.project):
        return _relative(ctx, path)
    return str(path)


def _hook_result(ctx: SetupContext, result: HookResult) -> StepResult:
    shown = _shown(ctx, result.path)
    bob = str(ctx.home.bin_bob)
    if result.state == "created":
        return StepResult(_INSTALLED, installed=(msg(_ITEM_HOOK, path=shown),))
    if result.state == "updated":
        return StepResult(
            _INSTALLED,
            installed=(msg(_ITEM_HOOK_UPDATED, path=shown),),
        )
    if result.state == "unchanged":
        return StepResult(_UNCHANGED)
    if result.state == "preserved":
        return StepResult(
            "preserved",
            preserved=(msg(_PRESERVED_HOOK, path=shown),),
            warnings=(msg(_WARN_HOOK_FOREIGN, path=shown, bob=bob),),
        )
    return StepResult(
        "preserved",
        preserved=(msg(_PRESERVED_HOOKSPATH, value=result.hooks_path),),
        warnings=(msg(_WARN_HOOKSPATH, value=result.hooks_path, bob=bob),),
    )


def _config_result(state: str, waivers: tuple[Text, ...]) -> StepResult:
    if state == "preserved":
        preserved = (msg(_PRESERVED_BOB_YAML),) + waivers
        return StepResult("preserved", preserved=preserved)
    return StepResult(
        _INSTALLED,
        installed=(msg(_ITEM_BOB_YAML),),
        preserved=waivers,
        warnings=_no_code_warning(state),
    )


def _no_code_warning(state: str) -> tuple[Text, ...]:
    if state == "created_no_code":
        return (msg(_WARN_NO_CODE),)
    return ()
