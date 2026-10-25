"""Workflow release: só workflow_dispatch, jobs check, verify e publish."""

from __future__ import annotations

import re
from pathlib import Path

import yaml

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "release.yml"
HARNESS = ROOT / "scripts" / "verify-install.sh"
USES = re.compile(r"^\s*(- )?uses: [\w./-]+@[0-9a-f]{40} # v\S+$")


def _text() -> str:
    return WORKFLOW.read_text(encoding="utf-8")


def _load() -> dict[str, object]:
    loaded = yaml.safe_load(_text())
    assert isinstance(loaded, dict)
    return loaded


def _on(doc: dict[str, object]) -> dict[str, object]:
    block = doc.get(True, doc.get("on"))
    assert isinstance(block, dict)
    return block


def _jobs(doc: dict[str, object]) -> dict[str, dict[str, object]]:
    jobs = doc["jobs"]
    assert isinstance(jobs, dict)
    typed: dict[str, dict[str, object]] = {}
    for name, job in jobs.items():
        assert isinstance(name, str)
        assert isinstance(job, dict)
        typed[name] = job
    return typed


def _steps(job: dict[str, object]) -> list[dict[str, object]]:
    steps = job["steps"]
    assert isinstance(steps, list)
    typed: list[dict[str, object]] = []
    for step in steps:
        assert isinstance(step, dict)
        typed.append(step)
    return typed


def _run_texts(node: object) -> list[str]:
    found: list[str] = []
    if isinstance(node, dict):
        run = node.get("run")
        if isinstance(run, str):
            found.append(run)
        for value in node.values():
            found.extend(_run_texts(value))
    elif isinstance(node, list):
        for item in node:
            found.extend(_run_texts(item))
    return found


def _dev_pin(name: str) -> str:
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    dev = tomllib.loads(text)["project"]["optional-dependencies"]["dev"]
    found = [item for item in dev if item.startswith(name + "==")]
    assert len(found) == 1
    return found[0].split(";", 1)[0].strip()


def _gitleaks_sha(name: str) -> str:
    match = re.search(rf"^{name}='([0-9a-f]{{64}})'$", _harness(), re.M)
    assert match is not None
    return match.group(1)


def _harness() -> str:
    return HARNESS.read_text(encoding="utf-8")


def test_release_runs_only_by_hand_on_main() -> None:
    doc = _load()
    trigger = _on(doc)
    assert set(trigger) == {"workflow_dispatch"}
    dispatch = trigger["workflow_dispatch"]
    assert isinstance(dispatch, dict)
    inputs = dispatch["inputs"]
    assert isinstance(inputs, dict)
    tag = inputs["tag"]
    prerelease = inputs["prerelease"]
    dry_run = inputs["dry_run"]
    assert isinstance(tag, dict)
    assert isinstance(prerelease, dict)
    assert isinstance(dry_run, dict)
    assert tag["required"] is True
    assert tag["type"] == "string"
    assert prerelease["type"] == "boolean"
    assert prerelease["default"] is True
    assert dry_run["type"] == "boolean"
    assert dry_run["default"] is False
    first = _steps(_jobs(doc)["check"])[0]
    run = first["run"]
    assert isinstance(run, str)
    assert "refs/heads/main" in run
    assert "exit 1" in run


def test_release_jobs_and_permissions() -> None:
    doc = _load()
    jobs = _jobs(doc)
    assert set(jobs) == {"check", "verify", "publish"}
    assert doc["permissions"] == {"contents": "read"}
    assert "permissions" not in jobs["check"]
    assert "permissions" not in jobs["verify"]
    assert jobs["publish"]["permissions"] == {"contents": "write"}
    assert jobs["verify"]["needs"] == "check"
    assert jobs["publish"]["needs"] == ["check", "verify"]
    assert jobs["publish"]["if"] == "${{ !inputs.dry_run }}"


def test_release_matrix_is_the_four_platforms() -> None:
    verify = _jobs(_load())["verify"]
    strategy = verify["strategy"]
    assert isinstance(strategy, dict)
    assert strategy["fail-fast"] is False
    matrix = strategy["matrix"]
    assert isinstance(matrix, dict)
    include = matrix["include"]
    assert isinstance(include, list)
    runners: list[str] = []
    for row in include:
        assert isinstance(row, dict)
        runner = row["runner"]
        gitleaks = row["gitleaks"]
        digest = row["gitleaks_sha256"]
        assert isinstance(runner, str)
        assert isinstance(gitleaks, str)
        assert isinstance(digest, str)
        runners.append(runner)
        assert digest == _gitleaks_sha("GITLEAKS_SHA_" + gitleaks.upper())
    assert runners == [
        "ubuntu-latest",
        "ubuntu-24.04-arm",
        "macos-15-intel",
        "macos-15",
    ]


def test_release_builds_the_three_assets() -> None:
    steps = _steps(_jobs(_load())["check"])
    build = next(
        step for step in steps if "python -m build" in str(step.get("run", ""))
    )
    run = build["run"]
    assert isinstance(run, str)
    assert f"'{_dev_pin('build')}'" in run
    assert f"'{_dev_pin('twine')}'" in run
    assert "twine check --strict" in run
    assert "cp scripts/install.sh dist/install.sh" in run
    assert "LC_ALL=C sort -k2 > SHA256SUMS" in run
    upload = next(
        step
        for step in steps
        if "upload-artifact" in str(step.get("uses", ""))
    )
    uploaded = upload["with"]
    assert isinstance(uploaded, dict)
    assert uploaded["name"] == "release-assets"


def test_release_verify_runs_the_verification_command() -> None:
    steps = _steps(_jobs(_load())["verify"])
    harness = next(
        step
        for step in steps
        if step.get("run") == "sh scripts/verify-install.sh"
    )
    env = harness["env"]
    assert isinstance(env, dict)
    assert "VERIFY_DIST" in env
    assert "TMPDIR" in env
    assert "PIP_CACHE_DIR" in env
    runs = "\n".join(
        run for step in steps if isinstance(run := step.get("run"), str)
    )
    assert "/tmp/dev/bin/pytest" in runs
    assert "/tmp/dev/bin/bob doctor" in runs
    assert "shasum -a 256 -c SHA256SUMS" in runs
    assert "cmp install.sh" in runs


def test_release_publish_creates_the_release_from_the_notes() -> None:
    steps = _steps(_jobs(_load())["publish"])
    create = next(
        step for step in steps if "gh release create" in str(step.get("run", ""))
    )
    run = create["run"]
    assert isinstance(run, str)
    assert "gh release create" in run
    assert '--target "$GITHUB_SHA"' in run
    assert "--notes-file" in run
    assert "docs/release-checks/$TAG.md" in run
    assert "--prerelease --latest=false" in run
    lines = [line.strip() for line in run.splitlines()]
    assert 'set -- "$@" --latest' in lines
    env = create["env"]
    assert isinstance(env, dict)
    assert env["GH_TOKEN"] == "${{ github.token }}"


def test_release_pins_actions_like_ci() -> None:
    text = _text()
    uses_lines = [line for line in text.splitlines() if "uses:" in line]
    assert uses_lines
    for line in uses_lines:
        assert USES.fullmatch(line)
    for forbidden in ("secrets.", "sudo", "pull_request", "push:"):
        assert forbidden not in text
    for run in _run_texts(_load()):
        assert "${{ inputs." not in run
