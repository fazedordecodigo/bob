from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import yaml

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "validate_cursor_plugin.py"
SCHEMA = ROOT / "scripts" / "cursor_plugin.schema.json"
SCHEMA_SHA256 = "31db124b1c7e43c22abb13ebf7e7c74556482e480fd492b80638d815c85b96b1"

EMPTY_MANIFEST_STDOUT = """[
  {
    "code": "schema",
    "subject": "/",
    "message": "'name' is a required property"
  },
  {
    "code": "name",
    "subject": "name",
    "message": "name must be bob"
  },
  {
    "code": "description",
    "subject": "description",
    "message": "description must be a non-empty string"
  },
  {
    "code": "version",
    "subject": "version",
    "message": "manifest <missing>, pyproject <missing>"
  },
  {
    "code": "logo",
    "subject": "assets/logo.svg",
    "message": "logo must be assets/logo.svg"
  },
  {
    "code": "readme",
    "subject": "README.md",
    "message": "README.md must be a regular file"
  }
]
"""


def _pyproject_version(root: Path = ROOT) -> str:
    loaded = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    project = loaded["project"]
    version = project["version"]
    if not isinstance(version, str) or not version:
        raise AssertionError("pyproject version is missing")
    return version


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        check=False,
        capture_output=True,
        text=True,
    )


def _manifest(**overrides: object) -> dict[str, object]:
    data: dict[str, object] = {
        "name": "bob",
        "description": "Quality gates for coding agents.",
        "version": "0.1.0",
        "logo": "assets/logo.svg",
    }
    data.update(overrides)
    return data


def _tree(tmp_path: Path, manifest: dict[str, object] | None = None) -> Path:
    root = tmp_path / "plugin"
    (root / ".cursor-plugin").mkdir(parents=True)
    (root / "assets").mkdir()
    payload = _manifest() if manifest is None else manifest
    (root / ".cursor-plugin" / "plugin.json").write_text(
        json.dumps(payload), encoding="utf-8"
    )
    (root / "pyproject.toml").write_text('[project]\nversion = "0.1.0"\n', encoding="utf-8")
    (root / "README.md").write_text(
        "## Usage\n\nIn a Python repository with `bob.yaml` and pytest:\n\nbob check --base main\n",
        encoding="utf-8",
    )
    (root / "assets" / "logo.svg").write_text(
        '<svg xmlns="http://www.w3.org/2000/svg"></svg>\n',
        encoding="utf-8",
    )
    return root


def test_schema_bytes_match_the_pinned_cursor_plugins_commit() -> None:
    digest = hashlib.sha256(SCHEMA.read_bytes()).hexdigest()
    assert digest == SCHEMA_SHA256


def test_real_tree_with_the_current_tag_prints_an_empty_list() -> None:
    tag = "v" + _pyproject_version()
    result = _run("--root", str(ROOT), "--tag", tag)
    assert (result.returncode, result.stdout, result.stderr) == (0, "[]\n", "")


def test_real_tree_without_a_tag_prints_an_empty_list() -> None:
    result = _run("--root", str(ROOT))
    assert (result.returncode, result.stdout, result.stderr) == (0, "[]\n", "")


def test_a_different_tag_names_the_three_versions() -> None:
    result = _run("--root", str(ROOT), "--tag", "v9.9.9")
    assert (result.returncode, result.stdout, result.stderr) == (
        1,
        json.dumps(
            [
                {
                    "code": "version",
                    "subject": "version",
                    "message": "manifest 0.1.0, pyproject 0.1.0, tag v9.9.9",
                }
            ],
            indent=2,
        )
        + "\n",
        "",
    )


def test_a_tag_without_the_v_prefix_is_rejected() -> None:
    result = _run("--root", str(ROOT), "--tag", "0.1.0")
    assert result.returncode == 1
    assert result.stderr == ""
    assert json.loads(result.stdout) == [
        {
            "code": "version",
            "subject": "version",
            "message": "manifest 0.1.0, pyproject 0.1.0, tag 0.1.0 is not v plus a semantic version",
        }
    ]


def test_an_empty_manifest_lists_every_missing_piece(tmp_path: Path) -> None:
    root = tmp_path / "empty"
    (root / ".cursor-plugin").mkdir(parents=True)
    (root / ".cursor-plugin" / "plugin.json").write_text("{}\n", encoding="utf-8")
    result = _run("--root", str(root))
    assert (result.returncode, result.stdout, result.stderr) == (1, EMPTY_MANIFEST_STDOUT, "")


def test_bad_argv_prints_usage_and_no_stdout() -> None:
    result = _run("--tag", "v0.1.0")
    assert (result.returncode, result.stdout, result.stderr) == (
        2,
        "",
        "usage: validate_cursor_plugin.py --root ROOT [--tag TAG]\n",
    )


def test_a_missing_root_is_exit_2(tmp_path: Path) -> None:
    missing = tmp_path / "absent"
    result = _run("--root", str(missing))
    assert (result.returncode, result.stdout, result.stderr) == (
        2,
        "",
        f"root is not a directory: {missing}\n",
    )


def test_an_http_uri_with_a_host_is_accepted(tmp_path: Path) -> None:
    root = _tree(
        tmp_path,
        _manifest(
            homepage="http://example.com/bob",
            repository="HTTPS://user:secret@github.com/fazedordecodigo/bob",
        ),
    )
    result = _run("--root", str(root))
    assert (result.returncode, result.stdout, result.stderr) == (0, "[]\n", "")


def test_a_uri_needs_http_or_https_and_a_host(tmp_path: Path) -> None:
    cases = (
        ("homepage", "not a url"),
        ("homepage", "ftp://example.com/plugin"),
        ("homepage", "https://"),
        ("homepage", "https://[::1"),
        ("repository", "javascript:alert(1)"),
        ("repository", "https:///missing-host"),
        ("repository", "http://"),
    )
    for index, (field, value) in enumerate(cases):
        root = _tree(tmp_path / str(index), _manifest(**{field: value}))
        result = _run("--root", str(root))
        assert result.returncode == 1, value
        assert result.stderr == "", value
        assert json.loads(result.stdout) == [
            {
                "code": "uri",
                "subject": field,
                "message": f"{field} must be an http or https URI with a host",
            }
        ]


def test_homepage_and_repository_uris_fail_independently(tmp_path: Path) -> None:
    root = _tree(
        tmp_path,
        _manifest(homepage="not a url", repository="ftp://example.com"),
    )
    result = _run("--root", str(root))
    assert result.returncode == 1
    assert result.stderr == ""
    assert json.loads(result.stdout) == [
        {
            "code": "uri",
            "subject": "homepage",
            "message": "homepage must be an http or https URI with a host",
        },
        {
            "code": "uri",
            "subject": "repository",
            "message": "repository must be an http or https URI with a host",
        },
    ]


def test_optimized_python_accepts_the_real_tree() -> None:
    tag = "v" + _pyproject_version()
    result = subprocess.run(
        [sys.executable, "-O", str(SCRIPT), "--root", str(ROOT), "--tag", tag],
        check=False,
        capture_output=True,
        text=True,
    )
    assert (result.returncode, result.stdout, result.stderr) == (0, "[]\n", "")


def test_an_extra_manifest_key_is_the_schema_message(tmp_path: Path) -> None:
    root = _tree(tmp_path, _manifest(extra=True))
    result = _run("--root", str(root))
    assert result.returncode == 1
    assert result.stderr == ""
    assert json.loads(result.stdout) == [
        {
            "code": "schema",
            "subject": "/",
            "message": "Additional properties are not allowed ('extra' was unexpected)",
        }
    ]


def test_a_blank_description_fails_after_the_schema(tmp_path: Path) -> None:
    root = _tree(tmp_path, _manifest(description="  "))
    result = _run("--root", str(root))
    assert result.returncode == 1
    assert json.loads(result.stdout) == [
        {
            "code": "description",
            "subject": "description",
            "message": "description must be a non-empty string",
        }
    ]


def test_a_parent_path_is_rejected(tmp_path: Path) -> None:
    root = _tree(tmp_path, _manifest(skills=["../secret"]))
    result = _run("--root", str(root))
    assert result.returncode == 1
    assert result.stderr == ""
    assert json.loads(result.stdout) == [
        {
            "code": "path",
            "subject": "../secret",
            "message": "path must be relative, start with ./, and contain no ..",
        }
    ]


def test_skill_frontmatter_name_must_match_the_folder(tmp_path: Path) -> None:
    root = _tree(tmp_path, _manifest(skills=["./skills/bob-check"]))
    skill = root / "skills" / "bob-check"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text(
        "---\nname: Bob_Check\ndescription: used when reviewing\n---\n\n# bob-check\n",
        encoding="utf-8",
    )
    result = _run("--root", str(root))
    assert result.returncode == 1
    assert result.stderr == ""
    assert json.loads(result.stdout) == [
        {
            "code": "frontmatter",
            "subject": "./skills/bob-check",
            "message": "name must be bob-check and kebab-case",
        }
    ]


def test_a_logo_left_out_of_head_fails(tmp_path: Path) -> None:
    root = _tree(tmp_path)
    logo = root / "assets" / "logo.svg"
    logo.unlink()
    subprocess.run(["git", "init"], cwd=root, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "bob@example.com"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.name", "bob"], cwd=root, check=True)
    subprocess.run(["git", "add", "."], cwd=root, check=True)
    subprocess.run(["git", "commit", "-m", "without logo"], cwd=root, check=True, capture_output=True)
    logo.write_text('<svg xmlns="http://www.w3.org/2000/svg"></svg>\n', encoding="utf-8")
    result = _run("--root", str(root))
    assert result.returncode == 1
    assert json.loads(result.stdout) == [
        {
            "code": "logo",
            "subject": "assets/logo.svg",
            "message": "logo file is not in HEAD",
        }
    ]


def test_publish_workflow_validates_and_does_not_upload() -> None:
    text = (ROOT / ".github" / "workflows" / "publish-plugins.yml").read_text(encoding="utf-8")
    assert "\n  cursor:\n" in text
    assert '- "v*"' in text
    assert "types:\n      - published\n" in text
    assert "dry_run:" in text
    assert "python scripts/validate_cursor_plugin.py" in text
    assert "contents: read" in text
    assert "secrets." not in text
    assert "marketplace/publish" not in text
    assert "jq " not in text
    assert "persist-credentials: false" in text
    loaded = yaml.safe_load(text)
    checkout = loaded["jobs"]["cursor"]["steps"][0]
    assert str(checkout["uses"]).startswith("actions/checkout@")
    assert checkout["with"]["persist-credentials"] is False
