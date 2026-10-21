"""bob setup (CT3): passos, resumo e código de saída."""

from __future__ import annotations

import hashlib
import importlib.metadata
import os
import platform
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

import pytest

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib

from bob_quality import cli, doctor, gitleaks, init_config, install_skills, npm_tools, setup_cmd
from bob_quality.config import ConfigError
from bob_quality.install_skills import SkillsResult, SourceError
from bob_quality.messages import Language, msg, reason, t
from bob_quality.gitleaks import GitleaksError
from bob_quality.npm_tools import PinSourceError
from bob_quality.setup_cmd import (
    STEPS,
    SetupContext,
    StepResult,
    run_setup,
    step_bob_yaml,
    step_gitleaks,
    step_npm,
    step_projeto,
    step_runtimes,
    step_skills,
)
from bob_quality.tools import ToolError
from bob_quality.user_dirs import bob_home

_SAMPLES = {
    "step": "projeto",
    "text": "texto",
    "items": "itens",
    "item": "item",
    "code": "0",
    "kind": "KeyError",
    "reason": "motivo",
    "path": "caminho",
    "value": "valor",
    "found": "achado",
    "floor": "1.2.3",
    "range": ">=1.2.3 <2",
    "major": "1",
    "detail": "detalhe",
    "names": "nomes",
    "version": "versão",
}

_MESSAGES = (
    (
        "cli.setup",
        "Set up bob in this project (npm tools, skills) and run bob doctor",
        "Prepara o bob neste projeto (ferramentas npm, skills) e roda o bob doctor",
    ),
    ("setup.step_ok", "bob setup: {step}: ok", "bob setup: {step}: ok"),
    (
        "setup.warning_line",
        "bob setup: {step}: warning: {text}",
        "bob setup: {step}: aviso: {text}",
    ),
    ("setup.error", "bob setup: {reason}", "bob setup: {reason}"),
    ("setup.summary", "bob setup: summary", "bob setup: resumo"),
    ("setup.installed", "  installed: {items}", "  instalado: {items}"),
    ("setup.nothing", "nothing", "nada"),
    ("setup.preserved", "  preserved: {item}", "  preservado: {item}"),
    ("setup.warnings", "  warnings: {text}", "  avisos: {text}"),
    ("setup.doctor", "  bob doctor: {code}", "  bob doctor: {code}"),
    ("setup.doctor_not_run", "not run", "não rodou"),
    (
        "setup.internal_error",
        "{step}: internal error ({kind}). Open an issue.",
        "{step}: erro interno ({kind}). Abra uma issue.",
    ),
    ("setup.step_reason", "{step}: {reason}", "{step}: {reason}"),
    (
        "setup.git_missing",
        "projeto: git not found. Install git and run again.",
        "projeto: git não encontrado. Instale o git e rode de novo.",
    ),
    (
        "setup.not_git_root",
        "projeto: {path} is not the root of a git repository. Run in the project root.",
        "projeto: {path} não é a raiz de um repositório git. Rode na raiz do projeto.",
    ),
    (
        "setup.bob_home_relative",
        "projeto: BOB_HOME={value} must be absolute. Use an absolute path.",
        "projeto: BOB_HOME={value} precisa ser absoluto. Use um caminho absoluto.",
    ),
    (
        "setup.python_floor_bad",
        "runtimes: Requires-Python = {value} is not >=A.B. Reinstall bob.",
        "runtimes: Requires-Python = {value} não é >=A.B. Reinstale o bob.",
    ),
    (
        "setup.python_old",
        "runtimes: found Python {found}, required >={floor}. "
        "Install Python {floor} or newer.",
        "runtimes: encontrado Python {found}, exigido >={floor}. "
        "Instale um Python {floor} ou mais novo.",
    ),
    (
        "setup.node_missing",
        "runtimes: node not found, required {range}. "
        "Install Node {floor} or newer from the {major} line.",
        "runtimes: node não encontrado, exigido {range}. "
        "Instale o Node {floor} ou mais novo da linha {major}.",
    ),
    (
        "setup.node_out",
        "runtimes: found node {found}, required {range}. "
        "Install Node {floor} or newer from the {major} line.",
        "runtimes: encontrado node {found}, exigido {range}. "
        "Instale o Node {floor} ou mais novo da linha {major}.",
    ),
    (
        "setup.npm_failed",
        "npm: npm ci failed. See the output above and run bob setup again.",
        "npm: npm ci falhou. Veja a saída acima e rode bob setup de novo.",
    ),
    (
        "setup.skills_source",
        "skills: {detail}. Reinstall bob.",
        "skills: {detail}. Reinstale o bob.",
    ),
    (
        "setup.skills_write",
        "skills: could not write {path} ({detail}). Check the permissions.",
        "skills: não consegui gravar {path} ({detail}). Confira as permissões.",
    ),
    ("setup.item_npm", "npm tools", "ferramentas npm"),
    (
        "setup.item_gitleaks",
        "gitleaks {version} in BOB_HOME/bin",
        "gitleaks {version} em BOB_HOME/bin",
    ),
    (
        "setup.item_skills",
        "skills ({names}) in .agents/skills",
        "skills ({names}) em .agents/skills",
    ),
    (
        "setup.preserved_no_marker",
        "{path} (no .bob-version)",
        "{path} (sem .bob-version)",
    ),
    ("setup.preserved_symlink", "{path} (symlink)", "{path} (link simbólico)"),
    ("setup.preserved_file", "{path} (file)", "{path} (arquivo)"),
    ("setup.preserved_foreign", "{path} (not from bob)", "{path} (não é do bob)"),
    (
        "setup.warn_no_marker",
        "{path} has no .bob-version and was left as is. "
        "If it is bob's, delete the folder and run bob setup again.",
        "{path} não tem .bob-version e ficou como está. "
        "Se ela é do bob, apague a pasta e rode bob setup de novo.",
    ),
    (
        "setup.warn_duplicate",
        "found a copy of bob in {path}. bob now uses only .agents/skills; "
        "delete {path} if you do not need it.",
        "achei uma cópia do bob em {path}. O bob agora usa só .agents/skills; "
        "apague {path} se não precisar dela.",
    ),
    ("setup.item_bob_yaml", "bob.yaml", "bob.yaml"),
    (
        "setup.preserved_bob_yaml",
        "bob.yaml (already exists; not changed)",
        "bob.yaml (já existe; sem mudanças)",
    ),
    (
        "setup.preserved_waivers",
        ".bob/waivers.yaml (bob does not change it)",
        ".bob/waivers.yaml (o bob não altera)",
    ),
    (
        "setup.warn_no_code",
        'no code folder found; paths.include: ["."].',
        'nenhuma pasta de código encontrada; paths.include: ["."].',
    ),
    (
        "setup.bob_yaml_invalid",
        "bob.yaml: the generated file is invalid ({detail}). Open an issue.",
        "bob.yaml: o arquivo gerado é inválido ({detail}). Abra uma issue.",
    ),
    (
        "setup.bob_yaml_write",
        "bob.yaml: could not write bob.yaml ({detail}). Check the permissions.",
        "bob.yaml: não consegui gravar bob.yaml ({detail}). Confira as permissões.",
    ),
)


def _git(cwd: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)


@pytest.fixture
def git_project(tmp_path: Path) -> Path:
    project = tmp_path / "proj"
    project.mkdir()
    _git(project, "init", "-q")
    _git(project, "config", "user.email", "t@t")
    _git(project, "config", "user.name", "t")
    _git(project, "config", "commit.gpgsign", "false")
    source = project / "src"
    source.mkdir()
    (source / "app.py").write_text("print(1)\n")
    _git(project, "add", "-A")
    _git(project, "commit", "-qm", "init")
    return project.resolve()


@pytest.fixture
def ctx(tmp_path: Path) -> Callable[..., SetupContext]:
    def make(project: Path, lang: Language = "en") -> SetupContext:
        return SetupContext(
            project,
            bob_home({"HOME": str(tmp_path / "home")}),
            lang,
            "1.2.3",
        )

    return make


def fake_step(result: StepResult) -> Callable[[SetupContext], StepResult]:
    def step(current: SetupContext) -> StepResult:
        step.calls.append(current)
        return result

    step.calls = []
    return step


def _folder(tmp_path: Path) -> Path:
    project = tmp_path / "p"
    project.mkdir()
    return project


def _pinned_node_text() -> str:
    node = npm_tools.node_range()
    return "v" + ".".join(str(part) for part in node.floor)


def _node_failure(key: str, found: str | None = None) -> StepResult:
    node = npm_tools.node_range()
    params: dict[str, object] = {
        "range": str(node),
        "floor": ".".join(map(str, node.floor)),
        "major": str(node.floor[0]),
    }
    if found is not None:
        params["found"] = found
    return StepResult("failed", error=msg(key, **params))


def _pass_doctor(code: int, text: str | None = None) -> Callable[..., int]:
    def run(install: bool, lang: str) -> int:
        run.seen.append((install, lang))
        if text is not None:
            print(text)
        return code

    run.seen = []
    return run


def _exercise_node_reader(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[dict[str, object]] = []

    def run(args: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        calls.append({"args": args, **kwargs})
        return subprocess.CompletedProcess(args, 0, stdout="v22.18.0\n", stderr="")

    def which(name: str) -> str | None:
        assert name == "node"
        return "/usr/bin/node"

    monkeypatch.setattr(setup_cmd.shutil, "which", which)
    monkeypatch.setattr(setup_cmd.subprocess, "run", run)
    assert setup_cmd._node_version_text() == "v22.18.0"
    assert calls[0]["args"] == ["/usr/bin/node", "--version"]
    assert calls[0]["capture_output"] is True
    assert calls[0]["text"] is True
    assert calls[0]["timeout"] == 30
    assert calls[0]["check"] is False

    monkeypatch.setattr(setup_cmd.shutil, "which", lambda name: None)
    assert setup_cmd._node_version_text() is None
    monkeypatch.setattr(setup_cmd.shutil, "which", lambda name: "/usr/bin/node")

    def failed(args: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(args, 1, stdout="v22.18.0\n", stderr="")

    monkeypatch.setattr(setup_cmd.subprocess, "run", failed)
    assert setup_cmd._node_version_text() is None

    def crashed(args: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        raise OSError("down")

    monkeypatch.setattr(setup_cmd.subprocess, "run", crashed)
    assert setup_cmd._node_version_text() is None

    def timed_out(args: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        raise subprocess.TimeoutExpired(args, 30)

    monkeypatch.setattr(setup_cmd.subprocess, "run", timed_out)
    assert setup_cmd._node_version_text() is None


def test_steps_follow_the_ct3_order() -> None:
    assert [step_id for step_id, _step in STEPS] == [
        "projeto",
        "runtimes",
        "npm",
        "gitleaks",
        "skills",
        "bob.yaml",
    ]
    assert dict(STEPS)["gitleaks"] is step_gitleaks
    assert dict(STEPS)["bob.yaml"] is step_bob_yaml


def test_all_steps_pass_and_doctor_0_exits_0(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    project = _folder(tmp_path)
    seen: list[SetupContext] = []

    def version(name: str) -> str:
        assert name == "bob-quality"
        return "9.9.9"

    def step_a(current: SetupContext) -> StepResult:
        seen.append(current)
        return StepResult("installed", installed=(msg("setup.item_npm"),))

    doctor_run = _pass_doctor(0, "DOCTOR")
    monkeypatch.setattr(setup_cmd.importlib.metadata, "version", version)
    monkeypatch.setattr(
        setup_cmd,
        "STEPS",
        (("a", step_a), ("b", fake_step(StepResult("unchanged")))),
    )
    monkeypatch.setattr(doctor, "run_doctor", doctor_run)
    link = tmp_path / "link"
    link.symlink_to(project)
    assert run_setup(link, "en") == 0
    captured = capsys.readouterr()
    assert captured.out == (
        "bob setup: a: ok\n"
        "bob setup: b: ok\n"
        "DOCTOR\n"
        "bob setup: summary\n"
        "  installed: npm tools\n"
        "  bob doctor: 0\n"
    )
    assert captured.err == ""
    assert seen[0].project == project.resolve()
    assert seen[0].version == "9.9.9"
    assert seen[0].lang == "en"
    assert doctor_run.seen == [(False, "en")]
    both = StepResult(
        "installed",
        installed=(msg("setup.item_npm"), msg("setup.item_skills", names="bob-check")),
    )
    monkeypatch.setattr(setup_cmd, "STEPS", (("a", fake_step(both)),))
    assert run_setup(project, "en") == 0
    joined = "  installed: npm tools, skills (bob-check) in .agents/skills"
    assert joined in capsys.readouterr().out.splitlines()


def test_doctor_4_makes_setup_exit_4(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    project = _folder(tmp_path)
    monkeypatch.setattr(setup_cmd, "STEPS", (("a", fake_step(StepResult("unchanged"))),))
    monkeypatch.setattr(doctor, "run_doctor", _pass_doctor(4))
    assert run_setup(project, "en") == 4
    assert capsys.readouterr().out.splitlines()[-1] == "  bob doctor: 4"
    monkeypatch.setattr(doctor, "run_doctor", _pass_doctor(1))
    assert run_setup(project, "en") == 4
    assert capsys.readouterr().out.splitlines()[-1] == "  bob doctor: 1"


@pytest.mark.parametrize("lang", ["en", "pt-BR"])
def test_first_failed_step_stops_and_prints_a_partial_summary(
    lang: Language,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    ran = {"c": False, "doctor": False}

    def step_c(current: SetupContext) -> StepResult:
        ran["c"] = True
        return StepResult("unchanged")

    def run_doctor(install: bool = False, lang: str = "en") -> int:
        ran["doctor"] = True
        return 0

    monkeypatch.setattr(
        setup_cmd,
        "STEPS",
        (
            ("a", fake_step(StepResult("installed", installed=(msg("setup.item_npm"),)))),
            ("b", fake_step(StepResult("failed", error=msg("setup.npm_failed")))),
            ("c", step_c),
        ),
    )
    monkeypatch.setattr(doctor, "run_doctor", run_doctor)
    assert run_setup(_folder(tmp_path), lang) == 4
    assert ran == {"c": False, "doctor": False}
    captured = capsys.readouterr()
    assert captured.err == t(lang, "setup.error", reason=t(lang, "setup.npm_failed")) + "\n"
    tail = "\n".join(
        [
            t(lang, "setup.summary"),
            t(lang, "setup.installed", items=t(lang, "setup.item_npm")),
            t(lang, "setup.doctor", code=t(lang, "setup.doctor_not_run")),
        ]
    )
    assert captured.out.endswith(tail + "\n")
    assert "bob setup: b: ok" not in captured.out


def test_exception_in_a_step_is_an_internal_error(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    def step_a(current: SetupContext) -> StepResult:
        raise KeyError("x")

    monkeypatch.setattr(setup_cmd, "STEPS", (("a", step_a),))
    project = _folder(tmp_path)
    assert run_setup(project, "en") == 4
    assert capsys.readouterr().err == (
        "bob setup: a: internal error (KeyError). Open an issue.\n"
    )

    def interrupt(current: SetupContext) -> StepResult:
        raise KeyboardInterrupt

    monkeypatch.setattr(setup_cmd, "STEPS", (("a", interrupt),))
    with pytest.raises(KeyboardInterrupt):
        run_setup(project, "en")


@pytest.mark.parametrize(
    ("lang", "line"),
    [("en", "  installed: nothing"), ("pt-BR", "  instalado: nada")],
)
def test_nothing_installed_says_nothing(
    lang: Language,
    line: str,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(setup_cmd, "STEPS", (("a", fake_step(StepResult("unchanged"))),))
    monkeypatch.setattr(doctor, "run_doctor", _pass_doctor(0))
    assert run_setup(_folder(tmp_path), lang) == 0
    assert line in capsys.readouterr().out.splitlines()


def test_preserved_and_warnings_lines_follow_the_ct3_order(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    preserved = (msg("setup.preserved_foreign", path=".agents/skills/outra"),)
    warnings = (msg("setup.warn_duplicate", path=".claude/skills/harden"),)
    step = fake_step(StepResult("unchanged", preserved=preserved, warnings=warnings))
    monkeypatch.setattr(setup_cmd, "STEPS", (("a", step),))
    monkeypatch.setattr(doctor, "run_doctor", _pass_doctor(0))
    project = _folder(tmp_path)
    assert run_setup(project, "en") == 0
    stdout = capsys.readouterr().out
    warning = (
        "bob setup: a: warning: found a copy of bob in .claude/skills/harden. "
        "bob now uses only .agents/skills; delete .claude/skills/harden "
        "if you do not need it."
    )
    assert f"bob setup: a: ok\n{warning}\n" in stdout
    summary = stdout.split("bob setup: summary\n", 1)[1]
    assert summary == (
        "  installed: nothing\n"
        "  preserved: .agents/skills/outra (not from bob)\n"
        "  warnings: found a copy of bob in .claude/skills/harden. "
        "bob now uses only .agents/skills; delete .claude/skills/harden "
        "if you do not need it.\n"
        "  bob doctor: 0\n"
    )
    assert run_setup(project, "pt-BR") == 0
    assert "bob setup: a: aviso: " in capsys.readouterr().out


@pytest.mark.parametrize("lang", ["en", "pt-BR"])
def test_relative_bob_home_fails_before_any_step(
    lang: Language,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("BOB_HOME", "rel")
    ran = {"step": False}

    def step(current: SetupContext) -> StepResult:
        ran["step"] = True
        return StepResult("unchanged")

    monkeypatch.setattr(setup_cmd, "STEPS", (("a", step),))
    assert run_setup(_folder(tmp_path), lang) == 4
    assert ran["step"] is False
    captured = capsys.readouterr()
    reason_line = t(lang, "setup.bob_home_relative", value="rel")
    assert captured.err == t(lang, "setup.error", reason=reason_line) + "\n"
    last = t(lang, "setup.doctor", code=t(lang, "setup.doctor_not_run"))
    assert captured.out.splitlines()[-1] == last


def test_projeto_accepts_the_git_root(
    ctx: Callable[..., SetupContext],
    git_project: Path,
) -> None:
    assert step_projeto(ctx(git_project)) == StepResult("unchanged")


def test_projeto_rejects_a_subfolder_and_a_plain_folder(
    monkeypatch: pytest.MonkeyPatch,
    ctx: Callable[..., SetupContext],
    git_project: Path,
    tmp_path: Path,
) -> None:
    plain = tmp_path / "plain"
    plain.mkdir()
    for path in (git_project / "src", plain):
        result = step_projeto(ctx(path))
        assert result == StepResult("failed", error=msg("setup.not_git_root", path=path))

    def failed_run(args: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        assert args == ["git", "rev-parse", "--show-toplevel"]
        assert kwargs["cwd"] == git_project
        assert kwargs["capture_output"] is True
        assert kwargs["text"] is True
        assert kwargs["check"] is False
        return subprocess.CompletedProcess(args, 1, stdout=str(git_project), stderr="")

    monkeypatch.setattr(setup_cmd.subprocess, "run", failed_run)
    missed = step_projeto(ctx(git_project))
    assert missed == StepResult("failed", error=msg("setup.not_git_root", path=git_project))

    def crashed(args: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        raise OSError("down")

    monkeypatch.setattr(setup_cmd.subprocess, "run", crashed)
    broken = step_projeto(ctx(git_project))
    assert broken == StepResult("failed", error=msg("setup.not_git_root", path=git_project))


def test_projeto_without_git(
    monkeypatch: pytest.MonkeyPatch,
    ctx: Callable[..., SetupContext],
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(setup_cmd.shutil, "which", lambda name: None)
    result = step_projeto(ctx(_folder(tmp_path)))
    assert result == StepResult("failed", error=msg("setup.git_missing"))


def test_runtimes_accepts_the_pinned_node(
    monkeypatch: pytest.MonkeyPatch,
    ctx: Callable[..., SetupContext],
    tmp_path: Path,
) -> None:
    _exercise_node_reader(monkeypatch)
    monkeypatch.setattr(setup_cmd, "_node_version_text", lambda: _pinned_node_text())
    assert step_runtimes(ctx(_folder(tmp_path))) == StepResult("unchanged")


@pytest.mark.parametrize(
    "found",
    ["v20.0.0", "v23.0.0", "v22.0.0", "22.18.0", "v22.18.0-rc.1"],
)
def test_runtimes_rejects_node_out_of_range(
    found: str,
    monkeypatch: pytest.MonkeyPatch,
    ctx: Callable[..., SetupContext],
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(setup_cmd, "_node_version_text", lambda: found)
    assert step_runtimes(ctx(_folder(tmp_path))) == _node_failure("setup.node_out", found)


def test_runtimes_without_node(
    monkeypatch: pytest.MonkeyPatch,
    ctx: Callable[..., SetupContext],
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(setup_cmd, "_node_version_text", lambda: None)
    project = _folder(tmp_path)
    assert step_runtimes(ctx(project)) == _node_failure("setup.node_missing")

    def bad_range() -> object:
        raise PinSourceError(msg("npm.pin_bad_node_range", value="nope"))

    monkeypatch.setattr(npm_tools, "node_range", bad_range)
    pin_error = PinSourceError(msg("npm.pin_bad_node_range", value="nope"))
    assert step_runtimes(ctx(project)) == StepResult(
        "failed",
        error=msg("setup.step_reason", step="runtimes", reason=reason(pin_error)),
    )


def test_runtimes_rejects_an_old_python(
    monkeypatch: pytest.MonkeyPatch,
    ctx: Callable[..., SetupContext],
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(setup_cmd, "_python_floor", lambda: (99, 0))
    project = _folder(tmp_path)
    assert step_runtimes(ctx(project)) == StepResult(
        "failed",
        error=msg("setup.python_old", found=platform.python_version(), floor="99.0"),
    )
    monkeypatch.setattr(setup_cmd, "_python_floor", lambda: sys.version_info[:2])
    monkeypatch.setattr(setup_cmd, "_node_version_text", lambda: _pinned_node_text())
    assert step_runtimes(ctx(project)).status == "unchanged"
    monkeypatch.setattr(setup_cmd.sys, "version_info", (3, 8, 1))
    monkeypatch.setattr(setup_cmd, "_python_floor", lambda: (3, 8))
    assert step_runtimes(ctx(project)).status == "unchanged"
    monkeypatch.setattr(setup_cmd, "_python_floor", lambda: (2, 0))
    assert step_runtimes(ctx(project)).status == "unchanged"
    monkeypatch.setattr(setup_cmd, "_python_floor", lambda: (8, 0))
    assert step_runtimes(ctx(project)).status == "failed"


def test_runtimes_reports_a_bad_requires_python(
    monkeypatch: pytest.MonkeyPatch,
    ctx: Callable[..., SetupContext],
    tmp_path: Path,
) -> None:
    def bad() -> tuple[int, int]:
        raise ValueError("~=3.10")

    monkeypatch.setattr(setup_cmd, "_python_floor", bad)
    result = step_runtimes(ctx(_folder(tmp_path)))
    assert result == StepResult("failed", error=msg("setup.python_floor_bad", value="~=3.10"))


def test_python_floor_comes_from_the_package_metadata(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    spec = tomllib.loads(Path("pyproject.toml").read_text())["project"]["requires-python"]
    major, minor = spec.removeprefix(">=").split(".")
    assert setup_cmd._python_floor() == (int(major), int(minor))

    def metadata(name: str) -> dict[str, str]:
        assert name == "bob-quality"
        return {"Requires-Python": "~=3.10"}

    monkeypatch.setattr(setup_cmd.importlib.metadata, "metadata", metadata)
    with pytest.raises(ValueError) as caught:
        setup_cmd._python_floor()
    assert str(caught.value) == "~=3.10"


def test_npm_step_skips_npm_ci_when_the_prefix_matches(
    monkeypatch: pytest.MonkeyPatch,
    ctx: Callable[..., SetupContext],
    tmp_path: Path,
) -> None:
    seen: list[str] = []

    def install(lang: str) -> int:
        seen.append(lang)
        return 0

    def installed(prefix: Path, name: str) -> str:
        assert prefix == tmp_path
        assert name == "a"
        return "1.0.0"

    monkeypatch.setattr(npm_tools, "pinned_npm_versions", lambda: {"a": "1.0.0"})
    monkeypatch.setattr(npm_tools, "npm_prefix", lambda: tmp_path)
    monkeypatch.setattr(npm_tools, "installed_npm_version", installed)
    monkeypatch.setattr(npm_tools, "install_npm_dependencies", install)
    assert step_npm(ctx(_folder(tmp_path))) == StepResult("unchanged")
    assert seen == []


def test_npm_step_runs_npm_ci_when_a_tool_is_missing(
    monkeypatch: pytest.MonkeyPatch,
    ctx: Callable[..., SetupContext],
    tmp_path: Path,
) -> None:
    seen: list[str] = []

    def install(lang: str) -> int:
        seen.append(lang)
        return 0

    def missing(prefix: Path, name: str) -> str:
        raise ToolError(msg("npm.deps_missing", hint="x"))

    monkeypatch.setattr(npm_tools, "pinned_npm_versions", lambda: {"a": "1.0.0"})
    monkeypatch.setattr(npm_tools, "npm_prefix", lambda: tmp_path)
    monkeypatch.setattr(npm_tools, "installed_npm_version", missing)
    monkeypatch.setattr(npm_tools, "install_npm_dependencies", install)
    project = _folder(tmp_path)
    current = ctx(project, lang="pt-BR")
    result = step_npm(current)
    assert result.status == "installed"
    assert result.installed == (msg("setup.item_npm"),)
    assert seen == ["pt-BR"]

    monkeypatch.setattr(npm_tools, "installed_npm_version", lambda prefix, name: "9.9.9")
    seen.clear()
    assert step_npm(current).status == "installed"
    assert seen == ["pt-BR"]

    def bad_prefix() -> Path:
        raise ToolError(msg("npm.manifest_missing"))

    monkeypatch.setattr(npm_tools, "npm_prefix", bad_prefix)
    seen.clear()
    assert step_npm(current).status == "installed"
    assert seen == ["pt-BR"]


def test_npm_step_fails_when_npm_ci_fails(
    monkeypatch: pytest.MonkeyPatch,
    ctx: Callable[..., SetupContext],
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(npm_tools, "pinned_npm_versions", lambda: {"a": "1.0.0"})
    monkeypatch.setattr(npm_tools, "npm_prefix", lambda: tmp_path)
    monkeypatch.setattr(npm_tools, "installed_npm_version", lambda prefix, name: None)
    project = _folder(tmp_path)
    for code in (4, 1):
        monkeypatch.setattr(npm_tools, "install_npm_dependencies", lambda lang: code)
        assert step_npm(ctx(project)) == StepResult("failed", error=msg("setup.npm_failed"))

    def bad_pins() -> dict[str, str]:
        raise PinSourceError(msg("npm.pin_not_json", detail="x"))

    monkeypatch.setattr(npm_tools, "pinned_npm_versions", bad_pins)
    pin_error = PinSourceError(msg("npm.pin_not_json", detail="x"))
    assert step_npm(ctx(project)) == StepResult(
        "failed",
        error=msg("setup.step_reason", step="npm", reason=reason(pin_error)),
    )


def test_skills_step_reports_installed_preserved_and_warnings(
    monkeypatch: pytest.MonkeyPatch,
    ctx: Callable[..., SetupContext],
    git_project: Path,
) -> None:
    alien = git_project / ".agents" / "skills" / "outra"
    alien.mkdir(parents=True)
    (alien / "SKILL.md").write_text("# outra\n")
    harden = git_project / ".agents" / "skills" / "harden"
    harden.mkdir()
    (harden / "SKILL.md").write_text("# harden\n")
    copy = git_project / ".claude" / "skills" / "bob-check"
    copy.mkdir(parents=True)
    (copy / "SKILL.md").write_text("# copy\n")
    result = step_skills(ctx(git_project))
    assert result.status == "installed"
    assert result.installed == (msg("setup.item_skills", names="bob-check, review-report"),)
    assert result.preserved == (
        msg("setup.preserved_no_marker", path=".agents/skills/harden"),
        msg("setup.preserved_foreign", path=".agents/skills/outra"),
    )
    assert result.warnings == (
        msg("setup.warn_no_marker", path=".agents/skills/harden"),
        msg("setup.warn_duplicate", path=".claude/skills/bob-check"),
    )
    link = git_project / "link-file"
    notes = git_project / "notes.txt"
    notes.write_text("x\n")
    link.symlink_to(notes)
    plain = git_project / "plain.txt"
    plain.write_text("y\n")
    other = git_project / "other"
    other.mkdir()

    def crafted(project: Path, version: str) -> SkillsResult:
        return SkillsResult(
            installed=(),
            unchanged=(),
            preserved=(link, notes, plain, other),
            duplicates=(),
            unmarked=(notes,),
        )

    monkeypatch.setattr(install_skills, "install_project_skills", crafted)
    classified = step_skills(ctx(git_project))
    assert classified.status == "unchanged"
    assert classified.preserved == (
        msg("setup.preserved_symlink", path="link-file"),
        msg("setup.preserved_no_marker", path="notes.txt"),
        msg("setup.preserved_file", path="plain.txt"),
        msg("setup.preserved_foreign", path="other"),
    )
    assert classified.warnings == (msg("setup.warn_no_marker", path="notes.txt"),)


def test_skills_step_second_run_is_unchanged(
    ctx: Callable[..., SetupContext],
    git_project: Path,
) -> None:
    current = ctx(git_project)
    step_skills(current)
    assert step_skills(current) == StepResult("unchanged")
    marker = git_project / ".agents" / "skills" / "bob-check" / ".bob-version"
    assert marker.read_text() == "1.2.3\n"


def test_skills_step_write_error(
    monkeypatch: pytest.MonkeyPatch,
    ctx: Callable[..., SetupContext],
    tmp_path: Path,
) -> None:
    def denied(project: Path, version: str) -> SkillsResult:
        raise PermissionError(13, "Permission denied", "/p/.agents/skills/x")

    monkeypatch.setattr(install_skills, "install_project_skills", denied)
    project = _folder(tmp_path)
    result = step_skills(ctx(project))
    assert result == StepResult(
        "failed",
        error=msg(
            "setup.skills_write",
            path="/p/.agents/skills/x",
            detail="Permission denied",
        ),
    )

    def nameless(project: Path, version: str) -> SkillsResult:
        raise OSError("boom")

    monkeypatch.setattr(install_skills, "install_project_skills", nameless)
    bare = step_skills(ctx(project))
    assert bare == StepResult(
        "failed",
        error=msg("setup.skills_write", path=".agents/skills", detail="OSError"),
    )


def test_skills_step_bad_source(
    monkeypatch: pytest.MonkeyPatch,
    ctx: Callable[..., SetupContext],
    tmp_path: Path,
) -> None:
    def bad(project: Path, version: str) -> SkillsResult:
        raise SourceError("manifesto inválido")

    monkeypatch.setattr(install_skills, "install_project_skills", bad)
    result = step_skills(ctx(_folder(tmp_path)))
    assert result == StepResult(
        "failed",
        error=msg("setup.skills_source", detail="manifesto inválido"),
    )


@pytest.mark.parametrize(
    ("lang", "key", "template"),
    [
        (lang, key, template)
        for key, en, pt in _MESSAGES
        for lang, template in (("en", en), ("pt-BR", pt))
    ],
)
def test_setup_messages_exist_in_both_languages(
    lang: Language,
    key: str,
    template: str,
) -> None:
    assert t(lang, key, **_SAMPLES) == template.format(**_SAMPLES)


def test_cli_setup_runs_in_the_cwd(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    git_project: Path,
) -> None:
    monkeypatch.chdir(git_project)
    monkeypatch.setattr(setup_cmd, "STEPS", (("a", fake_step(StepResult("unchanged"))),))

    def run_doctor(install: bool = False, lang: str = "en") -> int:
        assert install is False
        assert lang == "pt-BR"
        return 0

    monkeypatch.setattr(doctor, "run_doctor", run_doctor)
    assert cli.main(["setup", "--lang", "pt-BR"]) == 0
    assert "bob setup: resumo" in capsys.readouterr().out


def _sha_tree(root: Path) -> dict[str, str]:
    found: dict[str, str] = {}
    for path in sorted(root.rglob("*")):
        if path.is_file() and not path.is_symlink():
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            found[path.relative_to(root).as_posix()] = digest
    return found


def _mtimes(root: Path) -> dict[str, int]:
    found = {".": root.lstat().st_mtime_ns}
    for path in root.rglob("*"):
        found[path.relative_to(root).as_posix()] = path.lstat().st_mtime_ns
    return found


def test_setup_does_not_touch_the_project_package_files(
    monkeypatch: pytest.MonkeyPatch,
    git_project: Path,
    tmp_path: Path,
) -> None:
    package = git_project / "package.json"
    package.write_text('{"dependencies": {"vitest": "4.1.0"}}\n')
    installed = git_project / "node_modules" / "vitest"
    installed.mkdir(parents=True)
    (installed / "package.json").write_text('{"name": "vitest", "version": "4.1.0"}\n')
    before_package = hashlib.sha256(package.read_bytes()).hexdigest()
    before_modules = _sha_tree(git_project / "node_modules")
    monkeypatch.setattr(setup_cmd, "_node_version_text", lambda: _pinned_node_text())
    monkeypatch.setattr(npm_tools, "pinned_npm_versions", lambda: {"vitest": "4.1.0"})
    monkeypatch.setattr(npm_tools, "npm_prefix", lambda: tmp_path)
    monkeypatch.setattr(npm_tools, "installed_npm_version", lambda prefix, name: "4.1.0")

    def forbid(lang: str) -> int:
        raise AssertionError(lang)

    monkeypatch.setattr(npm_tools, "install_npm_dependencies", forbid)
    monkeypatch.setattr(gitleaks, "installed_version", lambda home: gitleaks.VERSION)
    monkeypatch.setattr(doctor, "run_doctor", _pass_doctor(0))
    assert run_setup(git_project, "en") == 0
    skills = git_project / ".agents" / "skills"
    stamped = _mtimes(skills)
    assert run_setup(git_project, "en") == 0
    assert hashlib.sha256(package.read_bytes()).hexdigest() == before_package
    assert _sha_tree(git_project / "node_modules") == before_modules
    assert _mtimes(skills) == stamped
    assert importlib.metadata.version("bob-quality")


def test_gitleaks_step_is_unchanged_when_present(
    monkeypatch: pytest.MonkeyPatch,
    ctx: Callable[..., SetupContext],
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(gitleaks, "installed_version", lambda home: "8.30.1")

    def forbid(home: object) -> None:
        raise AssertionError(home)

    monkeypatch.setattr(gitleaks, "ensure_gitleaks", forbid)
    assert step_gitleaks(ctx(tmp_path)) == StepResult("unchanged")


@pytest.mark.parametrize("found", [None, "8.29.0", "8.30.1-beta.1"])
def test_gitleaks_step_installs_when_missing(
    monkeypatch: pytest.MonkeyPatch,
    ctx: Callable[..., SetupContext],
    tmp_path: Path,
    found: str | None,
) -> None:
    seen: list[object] = []

    def install(home: object) -> None:
        seen.append(home)

    monkeypatch.setattr(gitleaks, "installed_version", lambda home: found)
    monkeypatch.setattr(gitleaks, "ensure_gitleaks", install)
    current = ctx(tmp_path)
    assert step_gitleaks(current) == StepResult(
        "installed",
        installed=(msg("setup.item_gitleaks", version="8.30.1"),),
    )
    assert seen[0] is current.home


@pytest.mark.parametrize("lang", ["en", "pt-BR"])
def test_gitleaks_step_failure_stops_setup(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
    lang: Language,
) -> None:
    asset = "gitleaks_8.30.1_linux_x64.tar.gz"

    def later(current: SetupContext) -> StepResult:
        raise AssertionError(current)

    monkeypatch.setattr(
        setup_cmd,
        "STEPS",
        (("gitleaks", step_gitleaks), ("b", later)),
    )
    monkeypatch.setattr(gitleaks, "installed_version", lambda home: None)

    def fail(home: object) -> None:
        raise GitleaksError(msg("gitleaks.integrity", asset=asset))

    monkeypatch.setattr(gitleaks, "ensure_gitleaks", fail)

    def doctor_run(install: bool = False, lang: str = "en") -> int:
        raise AssertionError((install, lang))

    monkeypatch.setattr(doctor, "run_doctor", doctor_run)
    project = tmp_path / "p"
    project.mkdir()
    assert run_setup(project, lang) == 4
    captured = capsys.readouterr()
    line = t(lang, "setup.error", reason=msg("gitleaks.integrity", asset=asset))
    assert line in captured.err.splitlines()
    assert "gitleaks" in line
    assert "sha256" in line
    assert captured.out.splitlines()[-1] == t(
        lang, "setup.doctor", code=t(lang, "setup.doctor_not_run")
    )


def test_gitleaks_step_passes_ctx_home_to_installed_version(
    monkeypatch: pytest.MonkeyPatch,
    ctx: Callable[..., SetupContext],
    tmp_path: Path,
) -> None:
    seen: list[object] = []

    def record(home: object) -> str:
        seen.append(home)
        return "8.30.1"

    def forbid(home: object) -> None:
        raise AssertionError(home)

    monkeypatch.setattr(gitleaks, "installed_version", record)
    monkeypatch.setattr(gitleaks, "ensure_gitleaks", forbid)
    current = ctx(tmp_path)
    assert step_gitleaks(current) == StepResult("unchanged")
    assert seen[0] is current.home


def test_gitleaks_step_reaches_the_summary(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(setup_cmd, "STEPS", (("gitleaks", step_gitleaks),))
    monkeypatch.setattr(gitleaks, "installed_version", lambda home: None)
    monkeypatch.setattr(gitleaks, "ensure_gitleaks", lambda home: home)
    monkeypatch.setattr(doctor, "run_doctor", _pass_doctor(0))
    project = tmp_path / "p"
    project.mkdir()
    assert run_setup(project, "en") == 0
    stdout = capsys.readouterr().out
    assert "bob setup: gitleaks: ok" in stdout
    assert "  installed: gitleaks 8.30.1 in BOB_HOME/bin" in stdout


def _empty_repo(tmp_path: Path) -> Path:
    empty_repo = tmp_path / "vazio"
    empty_repo.mkdir()
    _git(empty_repo, "init", "-q")
    return empty_repo.resolve()


def test_bob_yaml_step_reports_created(
    ctx: Callable[..., SetupContext],
    git_project: Path,
) -> None:
    result = step_bob_yaml(ctx(git_project))
    assert result == StepResult("installed", installed=(msg("setup.item_bob_yaml"),))
    text = (git_project / "bob.yaml").read_text(encoding="utf-8")
    assert "  include: [src]" in text


def test_bob_yaml_step_warns_when_there_is_no_code(
    ctx: Callable[..., SetupContext],
    tmp_path: Path,
) -> None:
    empty_repo = _empty_repo(tmp_path)
    assert step_bob_yaml(ctx(empty_repo)) == StepResult(
        "installed",
        installed=(msg("setup.item_bob_yaml"),),
        warnings=(msg("setup.warn_no_code"),),
    )


def test_bob_yaml_step_reports_preserved(
    ctx: Callable[..., SetupContext],
    git_project: Path,
) -> None:
    target = git_project / "bob.yaml"
    target.write_text("base: main\n", encoding="utf-8")
    before = target.read_bytes()
    assert step_bob_yaml(ctx(git_project)) == StepResult(
        "preserved",
        preserved=(msg("setup.preserved_bob_yaml"),),
    )
    assert target.read_bytes() == before


@pytest.mark.parametrize("shape", ["file", "symlink", "directory"])
def test_bob_yaml_step_lists_existing_waivers(
    ctx: Callable[..., SetupContext],
    git_project: Path,
    shape: str,
) -> None:
    waivers = git_project / ".bob" / "waivers.yaml"
    waivers.parent.mkdir()
    link_target = ""
    payload = b""
    if shape == "symlink":
        (git_project / "bob.yaml").write_text("base: main\n", encoding="utf-8")
        waivers.symlink_to("ausente")
        link_target = os.readlink(waivers)
    elif shape == "directory":
        waivers.mkdir()
    else:
        waivers.write_text("# w\n", encoding="utf-8")
        payload = waivers.read_bytes()
    result = step_bob_yaml(ctx(git_project))
    note = msg("setup.preserved_waivers")
    if shape == "symlink":
        assert result == StepResult(
            "preserved",
            preserved=(msg("setup.preserved_bob_yaml"), note),
        )
        assert os.readlink(waivers) == link_target
        return
    assert result == StepResult(
        "installed",
        installed=(msg("setup.item_bob_yaml"),),
        preserved=(note,),
    )
    if shape == "directory":
        assert waivers.is_dir()
        return
    assert waivers.read_bytes() == payload


def test_bob_yaml_step_invalid_config_fails(
    monkeypatch: pytest.MonkeyPatch,
    ctx: Callable[..., SetupContext],
    tmp_path: Path,
) -> None:
    def fail(project: Path) -> None:
        raise ConfigError("quebrado")

    monkeypatch.setattr(init_config, "write_default_config", fail)
    assert step_bob_yaml(ctx(tmp_path)) == StepResult(
        "failed",
        error=msg("setup.bob_yaml_invalid", detail="quebrado"),
    )


def test_bob_yaml_step_git_failure_fails(
    monkeypatch: pytest.MonkeyPatch,
    ctx: Callable[..., SetupContext],
    tmp_path: Path,
) -> None:
    cause = msg("git.ls_files_failed", detail="fatal: x")

    def fail(project: Path) -> None:
        raise ToolError(cause)

    monkeypatch.setattr(init_config, "write_default_config", fail)
    assert step_bob_yaml(ctx(tmp_path)) == StepResult(
        "failed",
        error=msg("setup.step_reason", step="bob.yaml", reason=cause),
    )


@pytest.mark.parametrize(
    ("exc", "detail"),
    [
        (PermissionError(13, "Permission denied"), "Permission denied"),
        (OSError(), "OSError"),
    ],
)
def test_bob_yaml_step_write_error_fails(
    monkeypatch: pytest.MonkeyPatch,
    ctx: Callable[..., SetupContext],
    tmp_path: Path,
    exc: OSError,
    detail: str,
) -> None:
    def fail(project: Path) -> None:
        raise exc

    monkeypatch.setattr(init_config, "write_default_config", fail)
    assert step_bob_yaml(ctx(tmp_path)) == StepResult(
        "failed",
        error=msg("setup.bob_yaml_write", detail=detail),
    )


@pytest.mark.parametrize("lang", ["en", "pt-BR"])
def test_bob_yaml_step_failure_stops_setup(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
    lang: Language,
) -> None:
    def later(current: SetupContext) -> StepResult:
        raise AssertionError(current)

    monkeypatch.setattr(
        setup_cmd,
        "STEPS",
        (("bob.yaml", step_bob_yaml), ("b", later)),
    )

    def fail(project: Path) -> None:
        raise ConfigError("quebrado")

    monkeypatch.setattr(init_config, "write_default_config", fail)

    def doctor_run(install: bool = False, lang: str = "en") -> int:
        raise AssertionError((install, lang))

    monkeypatch.setattr(doctor, "run_doctor", doctor_run)
    project = tmp_path / "p"
    project.mkdir()
    assert run_setup(project, lang) == 4
    captured = capsys.readouterr()
    line = t(
        lang,
        "setup.error",
        reason=msg("setup.bob_yaml_invalid", detail="quebrado"),
    )
    assert line in captured.err.splitlines()
    assert captured.out.splitlines()[-1] == t(
        lang,
        "setup.doctor",
        code=t(lang, "setup.doctor_not_run"),
    )


def test_bob_yaml_step_reaches_the_summary(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    git_project: Path,
) -> None:
    monkeypatch.setattr(setup_cmd, "STEPS", (("bob.yaml", step_bob_yaml),))
    monkeypatch.setattr(doctor, "run_doctor", _pass_doctor(0))
    waivers = git_project / ".bob" / "waivers.yaml"
    waivers.parent.mkdir()
    waivers.write_text("# w\n", encoding="utf-8")
    assert run_setup(git_project, "en") == 0
    stdout = capsys.readouterr().out
    assert "bob setup: bob.yaml: ok" in stdout.splitlines()
    assert "  installed: bob.yaml" in stdout.splitlines()
    kept = "  preserved: .bob/waivers.yaml (bob does not change it)"
    assert kept in stdout.splitlines()
    config_bytes = (git_project / "bob.yaml").read_bytes()
    waiver_bytes = waivers.read_bytes()
    assert run_setup(git_project, "en") == 0
    again = capsys.readouterr().out
    existing = "  preserved: bob.yaml (already exists; not changed)"
    assert existing in again.splitlines()
    assert again.index(existing) < again.index(kept)
    assert (git_project / "bob.yaml").read_bytes() == config_bytes
    assert waivers.read_bytes() == waiver_bytes


@pytest.mark.parametrize("lang", ["en", "pt-BR"])
def test_bob_yaml_step_no_code_warning_reaches_the_output(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
    lang: Language,
) -> None:
    monkeypatch.setattr(setup_cmd, "STEPS", (("bob.yaml", step_bob_yaml),))
    monkeypatch.setattr(doctor, "run_doctor", _pass_doctor(0))
    empty_repo = _empty_repo(tmp_path)
    assert run_setup(empty_repo, lang) == 0
    stdout = capsys.readouterr().out.splitlines()
    warning = t(lang, "setup.warn_no_code")
    assert t(lang, "setup.warning_line", step="bob.yaml", text=warning) in stdout
    assert t(lang, "setup.warnings", text=warning) in stdout
    text = (empty_repo / "bob.yaml").read_text(encoding="utf-8")
    assert '  include: ["."]' in text
