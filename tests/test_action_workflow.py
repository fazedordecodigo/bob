"""Contrato dos workflows: pytest no CI, action no PR, permissões e SHAs."""

import re
from pathlib import Path

import yaml

from bob_quality.doctor import NODE, node_admits

ROOT = Path(__file__).resolve().parents[1]
CI = ROOT / ".github" / "workflows" / "ci.yml"
BOB = ROOT / ".github" / "workflows" / "bob.yml"
ACTION = ROOT / ".github" / "actions" / "bob" / "action.yml"

PINNED = {
    "actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1",
    "actions/setup-python@5fda3b95a4ea91299a34e894583c3862153e4b97",
    "actions/upload-artifact@cf430e030ddbb5b0abf93d22962f4752f3646cd9",
    "actions/setup-node@49933ea5288caeca8642d1e84afbd3f7d6820020",
}
SHA = re.compile(r"@[0-9a-f]{40}$")


def _load(path: Path) -> dict[str, object]:
    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(loaded, dict)
    return loaded


def _on(doc: dict[str, object]) -> dict[str, object]:
    block = doc.get(True, doc.get("on"))
    assert isinstance(block, dict)
    return block


def _uses(node: object) -> list[str]:
    found: list[str] = []
    if isinstance(node, dict):
        uses = node.get("uses")
        if isinstance(uses, str):
            found.append(uses)
        for value in node.values():
            found.extend(_uses(value))
    elif isinstance(node, list):
        for item in node:
            found.extend(_uses(item))
    return found


def _assert_only_pinned_actions(doc: dict[str, object]) -> None:
    for uses in _uses(doc):
        if uses.startswith("./"):
            continue
        assert uses.split(" ", 1)[0] in PINNED or uses in PINNED
        pin = uses.split("@", 1)[1]
        assert SHA.search("@" + pin.split(" ", 1)[0])


def test_ci_runs_pytest_on_pull_requests_and_pushes_to_main() -> None:
    doc = _load(CI)
    trigger = _on(doc)
    push = trigger["push"]
    assert isinstance(push, dict)
    assert "main" in push["branches"]
    assert "pull_request" in trigger
    assert doc["permissions"] == {"contents": "read"}
    _assert_only_pinned_actions(doc)
    dumped = CI.read_text(encoding="utf-8")
    assert "pytest" in dumped
    assert "npm ci" in dumped
    assert "3.10" in dumped
    assert "3.12" in dumped
    assert "pull-requests:" not in dumped


def test_pull_request_workflow_dogfoods_the_local_action() -> None:
    doc = _load(BOB)
    trigger = _on(doc)
    assert "pull_request" in trigger
    assert "push" not in trigger
    permissions = doc["permissions"]
    assert permissions == {
        "contents": "read",
        "pull-requests": "write",
        "actions": "read",
    }
    _assert_only_pinned_actions(doc)
    uses = _uses(doc)
    assert "./.github/actions/bob" in uses
    text = BOB.read_text(encoding="utf-8")
    assert "fetch-depth: 0" in text
    assert "github.event.pull_request.head.sha" in text
    assert "github.base_ref" in text
    concurrency = doc["concurrency"]
    assert isinstance(concurrency, dict)
    assert concurrency["group"] == "bob-${{ github.event.pull_request.number }}"
    assert concurrency["cancel-in-progress"] is True
    jobs = doc["jobs"]
    assert isinstance(jobs, dict)
    check = jobs["check"]
    assert isinstance(check, dict)
    steps = check["steps"]
    assert isinstance(steps, list)
    fetch = next(step for step in steps if "git fetch" in str(step.get("run", "")))
    assert isinstance(fetch, dict)
    assert "${{" not in str(fetch["run"])
    env = fetch["env"]
    assert isinstance(env, dict)
    assert env["BASE_REF"] == "${{ github.base_ref }}"
    assert "$BASE_REF" in str(fetch["run"])
    assert any("npm ci" in str(step.get("run", "")) for step in steps)
    before_at = next(
        i for i, step in enumerate(steps) if step.get("name") == "DRY sem jscpd fica not run"
    )
    npm_at = next(i for i, step in enumerate(steps) if step.get("name") == "Ferramentas npm")
    action_at = next(i for i, step in enumerate(steps) if step.get("uses") == "./.github/actions/bob")
    after_at = next(i for i, step in enumerate(steps) if step.get("name") == "DRY rodou")
    assert before_at < npm_at < action_at < after_at
    after = steps[after_at]
    assert isinstance(after, dict)
    assert after["if"] == "always()"


def test_composite_action_comments_uploads_cache_and_keeps_bob_status() -> None:
    doc = _load(ACTION)
    runs = doc["runs"]
    assert isinstance(runs, dict)
    assert runs["using"] == "composite"
    inputs = doc["inputs"]
    assert isinstance(inputs, dict)
    gates = inputs["gates"]
    assert isinstance(gates, dict)
    assert gates["default"] == "crap,dry,deps,mutate"
    language = inputs["language"]
    assert isinstance(language, dict)
    assert language["required"] is False
    assert language["default"] == ""
    steps = runs["steps"]
    assert isinstance(steps, list)
    for step in steps:
        assert isinstance(step, dict)
        if "run" in step:
            assert step["shell"] == "bash"
    text = "\n".join(
        " ".join(str(step.get(key, "")) for key in ("uses", "run", "name")) for step in steps
    )
    restore = next(step for step in steps if "restore_cache.py" in str(step.get("run", "")))
    assert "||" in str(restore["run"])
    restore_env = restore["env"]
    assert isinstance(restore_env, dict)
    assert restore_env["GITHUB_BASE_REF"] == "${{ github.base_ref }}"
    assert restore_env["GITHUB_HEAD_REF"] == "${{ github.head_ref }}"
    assert text.index("restore_cache.py") < text.index("run_check.sh")
    assert text.index("run_check.sh") < text.index("upload-artifact")
    assert text.index("upload-artifact") < text.index("upsert_comment.py")
    assert text.index("upsert_comment.py") < text.index("propagate_exit.sh")
    upload = next(step for step in steps if "upload-artifact" in str(step.get("uses", "")))
    assert upload["if"] == "always()"
    with_block = upload["with"]
    assert isinstance(with_block, dict)
    assert with_block["name"] == "bob-mutation-cache"
    assert with_block["path"].splitlines() == [
        ".bob/mutation-cache.json",
        ".bob/stryker-incremental.json",
    ]
    assert with_block["if-no-files-found"] == "ignore"
    assert with_block["include-hidden-files"] is True
    assert with_block["retention-days"] == 7
    node = next(step for step in steps if "setup-node" in str(step.get("uses", "")))
    node_with = node["with"]
    assert isinstance(node_with, dict)
    assert node_with["node-version"] == "22.18.0"
    assert "49933ea5288caeca8642d1e84afbd3f7d6820020" in str(node["uses"])
    jscpd = next(step for step in steps if "install_jscpd.sh" in str(step.get("run", "")))
    assert jscpd.get("env", {}).get("JSCPD_VERSION") == "5.4.1"
    assert text.index("setup-node") < text.index("install.sh")
    assert text.index("install.sh") < text.index("install_jscpd.sh")
    assert text.index("install_jscpd.sh") < text.index("run_check.sh")
    check = next(step for step in steps if "run_check.sh" in str(step.get("run", "")))
    check_env = check["env"]
    assert isinstance(check_env, dict)
    assert check_env["BOB_LANGUAGE"] == "${{ inputs.language }}"
    comment = next(step for step in steps if "upsert_comment.py" in str(step.get("run", "")))
    comment_env = comment["env"]
    assert isinstance(comment_env, dict)
    assert comment_env["BOB_LANGUAGE"] == "${{ inputs.language }}"
    assert "always()" in str(comment["if"])
    assert "pull_request" in str(comment["if"])
    propagate = next(step for step in steps if "propagate_exit.sh" in str(step.get("run", "")))
    assert propagate["if"] == "always()"
    _assert_only_pinned_actions(doc)
    joined = ACTION.read_text(encoding="utf-8")
    assert "ghp_" not in joined
    assert "github_pat_" not in joined


def _setup_node_versions(path: Path) -> list[str]:
    found: list[str] = []
    _collect_setup_node_versions(_load(path), found)
    return found


def _collect_setup_node_versions(node: object, found: list[str]) -> None:
    if isinstance(node, dict):
        uses = node.get("uses")
        if isinstance(uses, str) and uses.split("@", 1)[0].endswith("setup-node"):
            with_block = node.get("with")
            assert isinstance(with_block, dict)
            version = with_block["node-version"]
            assert isinstance(version, str)
            found.append(version)
        for value in node.values():
            _collect_setup_node_versions(value, found)
    elif isinstance(node, list):
        for item in node:
            _collect_setup_node_versions(item, found)


def test_workflows_install_a_node_the_doctor_accepts() -> None:
    package = ROOT / ".github" / "workflows" / "package.yml"
    counts = {ACTION: 1, CI: 1, BOB: 2, package: 1}
    for path, count in counts.items():
        versions = _setup_node_versions(path)
        assert len(versions) == count, path
        for version in versions:
            assert node_admits(NODE, version) is True, (path, version)


def test_dependabot_ignores_sonarjs_majors_and_scans_the_action() -> None:
    path = ROOT / ".github" / "dependabot.yml"
    loaded = _load(path)
    updates = loaded["updates"]
    assert isinstance(updates, list)
    npm = next(
        item
        for item in updates
        if isinstance(item, dict) and item.get("package-ecosystem") == "npm"
    )
    assert npm["ignore"] == [
        {
            "dependency-name": "eslint-plugin-sonarjs",
            "update-types": ["version-update:semver-major"],
        }
    ]
    actions = next(
        item
        for item in updates
        if isinstance(item, dict) and item.get("package-ecosystem") == "github-actions"
    )
    assert actions["directories"] == ["/", "/.github/actions/bob"]
    text = path.read_text(encoding="utf-8")
    assert "The lockfile must not be regenerated from scratch." in text
