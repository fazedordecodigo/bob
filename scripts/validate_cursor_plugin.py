from __future__ import annotations

import json
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Literal
from urllib.parse import urlparse

import yaml
from jsonschema import Draft7Validator

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

SCHEMA_PATH = Path(__file__).with_name("cursor_plugin.schema.json")
USAGE = "usage: validate_cursor_plugin.py --root ROOT [--tag TAG]"
PATH_FIELDS = ("skills", "rules", "agents", "commands", "hooks", "mcpServers")
LOGO_PATH = "assets/logo.svg"
FailureCode = Literal[
    "manifest",
    "schema",
    "name",
    "description",
    "version",
    "path",
    "frontmatter",
    "logo",
    "readme",
    "uri",
]
URI_FIELDS = ("homepage", "repository")


@dataclass(frozen=True)
class Failure:
    code: FailureCode
    subject: str
    message: str


@dataclass(frozen=True)
class ResolvedSkill:
    raw: str
    directory: Path


def _schema_error(message: str) -> str:
    return f"{message}: {SCHEMA_PATH}"


def _schema_mapping(value: object, detail: str) -> dict[str, object]:
    if isinstance(value, dict):
        return value
    raise RuntimeError(_schema_error(detail))


def _schema_text(value: object, detail: str) -> str:
    if isinstance(value, str):
        return value
    raise RuntimeError(_schema_error(detail))


def _load_tool_schema() -> dict[str, object] | str:
    if not SCHEMA_PATH.is_file():
        return _schema_error("schema file not found")
    try:
        loaded = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return _schema_error("schema file is not valid JSON")
    if not isinstance(loaded, dict):
        return _schema_error("schema file is not valid JSON")
    pattern = loaded.get("properties")
    name_pattern = pattern.get("name", {}).get("pattern") if isinstance(pattern, dict) else None
    if not isinstance(name_pattern, str):
        return _schema_error("schema file has no name pattern")
    defs = loaded.get("$defs")
    semver = defs.get("semver", {}).get("pattern") if isinstance(defs, dict) else None
    if not isinstance(semver, str) or not semver.startswith("^") or not semver.endswith("$"):
        return _schema_error("schema semver pattern is not anchored")
    return loaded


def _load_manifest(root: Path) -> dict[str, object] | Failure:
    path = root / ".cursor-plugin" / "plugin.json"
    if not path.is_file():
        return Failure("manifest", ".cursor-plugin/plugin.json", "manifest file is missing")
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return Failure(
            "manifest",
            ".cursor-plugin/plugin.json",
            f"manifest JSON is invalid: {exc.msg}",
        )
    if not isinstance(loaded, dict):
        return Failure("manifest", ".cursor-plugin/plugin.json", "manifest is not a JSON object")
    return loaded


def _schema_failures(manifest: dict[str, object], schema: dict[str, object]) -> tuple[Failure, ...]:
    validator = Draft7Validator(schema)
    failures: list[Failure] = []
    for error in validator.iter_errors(manifest):
        parts = [str(part) for part in error.absolute_path]
        subject = "/" if not parts else "/" + "/".join(parts)
        failures.append(Failure("schema", subject, error.message))
    return tuple(failures)


def _name_failures(manifest: dict[str, object]) -> tuple[Failure, ...]:
    if manifest.get("name") == "bob":
        return ()
    return (Failure("name", "name", "name must be bob"),)


def _description_failures(manifest: dict[str, object]) -> tuple[Failure, ...]:
    description = manifest.get("description")
    if isinstance(description, str) and description.strip():
        return ()
    return (Failure("description", "description", "description must be a non-empty string"),)


def _project_version(root: Path) -> str:
    path = root / "pyproject.toml"
    if not path.is_file():
        return "<missing>"
    try:
        loaded = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError):
        return "<missing>"
    project = loaded.get("project")
    if not isinstance(project, dict):
        return "<missing>"
    version = project.get("version")
    if not isinstance(version, str):
        return "<missing>"
    return version


def _version_token(value: object) -> str:
    if isinstance(value, str):
        return value
    return "<missing>"


def _version_failures(
    root: Path,
    manifest: dict[str, object],
    tag: str | None,
    schema: dict[str, object],
) -> tuple[Failure, ...]:
    raw_version = manifest.get("version")
    manifest_version = _version_token(raw_version)
    project_version = _project_version(root)
    if tag is None:
        if isinstance(raw_version, str) and manifest_version == project_version:
            return ()
        return (
            Failure(
                "version",
                "version",
                f"manifest {manifest_version}, pyproject {project_version}",
            ),
        )
    pattern = _semver_pattern(schema)
    if re.fullmatch("v" + pattern[1:-1], tag) and manifest_version == project_version == tag[1:]:
        return ()
    if re.fullmatch("v" + pattern[1:-1], tag):
        message = f"manifest {manifest_version}, pyproject {project_version}, tag {tag}"
    else:
        message = (
            f"manifest {manifest_version}, pyproject {project_version}, "
            f"tag {tag} is not v plus a semantic version"
        )
    return (Failure("version", "version", message),)


def _semver_pattern(schema: dict[str, object]) -> str:
    detail = "schema semver pattern is not anchored"
    defs = _schema_mapping(schema.get("$defs"), detail)
    semver = _schema_mapping(defs.get("semver"), detail)
    pattern = _schema_text(semver.get("pattern"), detail)
    if pattern.startswith("^") and pattern.endswith("$"):
        return pattern
    raise RuntimeError(_schema_error(detail))


def _name_pattern(schema: dict[str, object]) -> str:
    detail = "schema file has no name pattern"
    properties = _schema_mapping(schema.get("properties"), detail)
    name_schema = _schema_mapping(properties.get("name"), detail)
    return _schema_text(name_schema.get("pattern"), detail)


def _http_uri(value: str) -> bool:
    try:
        parsed = urlparse(value)
        host = parsed.hostname
    except ValueError:
        return False
    return parsed.scheme.lower() in {"http", "https"} and bool(host)


def _uri_failures(manifest: dict[str, object]) -> tuple[Failure, ...]:
    failures: list[Failure] = []
    for field in URI_FIELDS:
        if field not in manifest:
            continue
        value = manifest[field]
        if not isinstance(value, str) or _http_uri(value):
            continue
        failures.append(
            Failure("uri", field, f"{field} must be an http or https URI with a host")
        )
    return tuple(failures)


def _relative_path(raw: str) -> bool:
    if "\\" in raw or not raw.startswith("./"):
        return False
    path = Path(raw)
    if path.is_absolute() or raw.startswith("/") or ".." in path.parts:
        return False
    return True


def _path_item(
    root: Path, raw: str, field: str
) -> Failure | ResolvedSkill | None:
    if not _relative_path(raw):
        return Failure("path", raw, "path must be relative, start with ./, and contain no ..")
    candidate = root / raw
    if candidate.is_symlink():
        return Failure("path", raw, "path is a symlink")
    if field == "skills":
        if not candidate.exists():
            return Failure("path", raw, "path does not exist")
        if not candidate.is_dir():
            return Failure("path", raw, "skill path is not a directory")
        skill_md = candidate / "SKILL.md"
        if skill_md.is_symlink():
            return Failure("path", raw, "SKILL.md is a symlink")
        if not skill_md.is_file():
            return Failure("path", raw, "skill path has no SKILL.md")
        return ResolvedSkill(raw, candidate)
    if not candidate.exists():
        return Failure("path", raw, "path does not exist")
    return None


def _string_items(value: object) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [item for item in value if isinstance(item, str)]
    return []


def _paths(root: Path, manifest: dict[str, object]) -> tuple[tuple[Failure, ...], tuple[ResolvedSkill, ...]]:
    failures: list[Failure] = []
    skills: list[ResolvedSkill] = []
    for field in PATH_FIELDS:
        if field not in manifest:
            continue
        for raw in _string_items(manifest[field]):
            item = _path_item(root, raw, field)
            if isinstance(item, Failure):
                failures.append(item)
            elif isinstance(item, ResolvedSkill):
                skills.append(item)
    return tuple(failures), tuple(skills)


def _frontmatter_failures(
    skills: tuple[ResolvedSkill, ...], name_pattern: re.Pattern[str]
) -> tuple[Failure, ...]:
    failures: list[Failure] = []
    for skill in skills:
        text = (skill.directory / "SKILL.md").read_text(encoding="utf-8")
        if not text.startswith("---\n"):
            failures.append(
                Failure("frontmatter", skill.raw, "frontmatter is missing or not closed")
            )
            continue
        parts = text.split("---\n", 2)
        if len(parts) < 3:
            failures.append(
                Failure("frontmatter", skill.raw, "frontmatter is missing or not closed")
            )
            continue
        try:
            loaded = yaml.safe_load(parts[1])
        except yaml.YAMLError:
            failures.append(Failure("frontmatter", skill.raw, "frontmatter YAML is invalid"))
            continue
        if not isinstance(loaded, dict):
            failures.append(Failure("frontmatter", skill.raw, "frontmatter is not a mapping"))
            continue
        folder = skill.directory.name
        name = loaded.get("name")
        if not isinstance(name, str) or name != folder or name_pattern.fullmatch(name) is None:
            failures.append(
                Failure("frontmatter", skill.raw, f"name must be {folder} and kebab-case")
            )
        description = loaded.get("description")
        if not isinstance(description, str) or not description.strip():
            failures.append(
                Failure("frontmatter", skill.raw, "description must be a non-empty string")
            )
    return tuple(failures)


def _logo_failures(root: Path, manifest: dict[str, object]) -> tuple[Failure, ...]:
    subject = LOGO_PATH
    if manifest.get("logo") != LOGO_PATH:
        return (Failure("logo", subject, "logo must be assets/logo.svg"),)
    path = root / LOGO_PATH
    if path.is_symlink():
        return (Failure("logo", subject, "logo file is a symlink"),)
    if not path.is_file():
        return (Failure("logo", subject, "logo file is not a regular file"),)
    try:
        text = path.read_bytes().decode("utf-8")
    except UnicodeDecodeError:
        return (Failure("logo", subject, "logo file must be UTF-8 SVG"),)
    if "<svg" not in text:
        return (Failure("logo", subject, "logo file must be UTF-8 SVG"),)
    if (root / ".git").exists():
        found = subprocess.run(
            ["git", "-C", str(root), "cat-file", "-e", f"HEAD:{LOGO_PATH}"],
            check=False,
            capture_output=True,
        )
        if found.returncode != 0:
            return (Failure("logo", subject, "logo file is not in HEAD"),)
    return ()


def _readme_failures(root: Path) -> tuple[Failure, ...]:
    path = root / "README.md"
    if path.is_symlink() or not path.is_file():
        return (Failure("readme", "README.md", "README.md must be a regular file"),)
    lines = path.read_text(encoding="utf-8").splitlines()
    headings = [index for index, line in enumerate(lines) if line == "## Usage"]
    if len(headings) != 1:
        return (
            Failure(
                "readme",
                "README.md",
                "README.md must contain one line that is exactly ## Usage",
            ),
        )
    section: list[str] = []
    for line in lines[headings[0] + 1 :]:
        if line.startswith("# ") or line.startswith("## "):
            break
        section.append(line)
    body = "\n".join(section)
    if "bob check" not in body or "bob.yaml" not in body:
        return (
            Failure(
                "readme",
                "README.md",
                "the Usage section must contain bob check and bob.yaml",
            ),
        )
    return ()


def validate(root: Path, tag: str | None) -> tuple[Failure, ...]:
    loaded = _load_manifest(root)
    if isinstance(loaded, Failure):
        return (loaded,)
    schema = _load_tool_schema()
    if isinstance(schema, str):
        raise RuntimeError(schema)
    path_failures, skills = _paths(root, loaded)
    return (
        _schema_failures(loaded, schema)
        + _name_failures(loaded)
        + _description_failures(loaded)
        + _uri_failures(loaded)
        + _version_failures(root, loaded, tag, schema)
        + path_failures
        + _frontmatter_failures(skills, re.compile(_name_pattern(schema)))
        + _logo_failures(root, loaded)
        + _readme_failures(root)
    )


def _parse(argv: list[str]) -> tuple[str, str | None] | None:
    root: str | None = None
    tag: str | None = None
    seen_tag = False
    index = 0
    while index < len(argv):
        arg = argv[index]
        if arg in {"--root", "--tag"}:
            if index + 1 >= len(argv):
                return None
            value = argv[index + 1]
            if arg == "--root":
                root = value
            else:
                tag = value
                seen_tag = True
            index += 2
            continue
        return None
    if root is None:
        return None
    return root, tag if seen_tag else None


def _dump(failures: tuple[Failure, ...]) -> str:
    payload = [
        {"code": item.code, "subject": item.subject, "message": item.message} for item in failures
    ]
    return json.dumps(payload, indent=2, ensure_ascii=False) + "\n"


def main(argv: list[str]) -> int:
    parsed = _parse(argv)
    if parsed is None:
        sys.stderr.write(USAGE + "\n")
        return 2
    root_text, tag = parsed
    root = Path(root_text)
    if not root.is_dir():
        sys.stderr.write(f"root is not a directory: {root_text}\n")
        return 2
    schema = _load_tool_schema()
    if isinstance(schema, str):
        sys.stderr.write(schema + "\n")
        return 2
    failures = validate(root, tag)
    sys.stdout.write(_dump(failures))
    if failures:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
