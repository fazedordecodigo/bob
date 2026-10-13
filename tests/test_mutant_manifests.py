from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from helpers import _git
from bob_quality.adapters.manifests import (
    AddedPackage,
    _Decl,
    _base_names,
    _declarations,
    _enter_section,
    _excluded,
    _git_show,
    _header,
    _inline_version,
    _keep,
    _lock_field,
    _manifest_name,
    _manifests,
    _missing_blob,
    _npm_line,
    _npm_lock_file,
    _npm_locked,
    _npm_row,
    _npm_skip,
    _opens_requirement_array,
    _package_on_line,
    _poetry_row,
    _poetry_section,
    _poetry_skips,
    _poetry_version,
    _python_declarations,
    _python_locked,
    _quoted_value,
    _requirement,
    _requirement_declarations,
    _root_manifests,
    _spec,
    _toml_lock,
    added_packages,
)


def test_enter_section_returns_the_brace_depth_only_for_that_section() -> None:
    assert _enter_section('"dependencies": { }', "dependencies") == (0, True)
    assert _enter_section('"other": { }', "dependencies") == (0, False)


def test_header_needs_both_brackets() -> None:
    assert _header("[project]") == "project"
    assert _header("[project") is None
    assert _header("project]") is None


def test_inline_version_reads_the_first_quote_after_the_first_version() -> None:
    assert _inline_version('x "nope" version "1.2.3"') == "1.2.3"
    assert _inline_version('version "1.2.3 version"') == "1.2.3 version"
    assert _inline_version('version "1.2.3" version "9.9.9"') == "1.2.3"


def test_lock_field_returns_only_a_non_empty_string() -> None:
    assert _lock_field({"left-pad": {"version": "1.2.3"}}, "left-pad") == "1.2.3"
    assert _lock_field({"left-pad": {"version": ""}}, "left-pad") is None
    assert _lock_field({"left-pad": {"version": 1}}, "left-pad") is None


def test_manifest_name_matches_the_index_and_the_filename() -> None:
    assert _manifest_name("package.json", "npm") is True
    assert _manifest_name("package.json", "pypi") is False
    assert _manifest_name("pyproject.toml", "pypi") is True
    assert _manifest_name("PYPROJECT.TOML", "pypi") is False
    assert _manifest_name("requirements.txt", "pypi") is True
    assert _manifest_name("requirements.md", "pypi") is False
    assert _manifest_name("notes.txt", "pypi") is False
    assert _manifest_name("REQUIREMENTS.txt", "pypi") is False
    assert _manifest_name("requirements.TXT", "pypi") is False


def test_missing_blob_accepts_either_git_phrase() -> None:
    assert _missing_blob("fatal: path 'a' does not exist in 'main'") is True
    assert _missing_blob("fatal: path 'a' exists on disk, but not in 'main'") is True
    assert _missing_blob("fatal: bad revision") is False


def test_npm_skip_rejects_file_dot_and_root_specs() -> None:
    assert _npm_skip("file:../local") is True
    assert _npm_skip("./local") is True
    assert _npm_skip("/local") is True
    assert _npm_skip("1.2.3") is False


def test_npm_row_drops_a_name_or_spec_that_is_not_a_string() -> None:
    text = '{\n  "dependencies": {\n    "1": "1.2.3"\n  }\n}\n'

    assert _npm_row(text, "dependencies", 1, "1.2.3") is None
    assert _npm_row(text, "dependencies", "left-pad", 1) is None
    assert _npm_row(text, "dependencies", "1", "1.2.3") == _Decl("1", "1.2.3", 3)


def test_npm_line_stays_inside_the_named_section() -> None:
    inside = '{\n  "dependencies": {\n    "left-pad": "1.2.3"\n  }\n}\n'
    name_first = '{\n  "name": "left-pad",\n  "dependencies": {\n    "other": "1.0.0"\n  }\n}\n'
    closed = (
        '{\n  "dependencies": {\n    "other": "1.0.0"\n  },\n'
        '  "devDependencies": {\n    "left-pad": "1.2.3"\n  }\n}\n'
    )
    nested = (
        '{\n  "dependencies": {\n    "obj": {\n      "x": 1\n    },\n'
        '    "left-pad": "1.2.3"\n  }\n}\n'
    )
    earlier = (
        '{\n  "dependencies": {\n'
        '    "left-pad": "1.2.3", "dependencies": "x"\n  }\n}\n'
    )

    assert _npm_line(inside, "dependencies", "left-pad") == 3
    assert _npm_line(name_first, "dependencies", "left-pad") is None
    assert _npm_line(closed, "dependencies", "left-pad") is None
    assert _npm_line(nested, "dependencies", "left-pad") == 6
    assert _npm_line(earlier, "dependencies", "left-pad") is None


def test_package_on_line_keeps_a_name_after_the_first_section_token() -> None:
    line = '"dependencies" "left-pad" "dependencies" "nope"'

    assert _package_on_line(line, "dependencies", "left-pad") is True


def test_opens_requirement_array_matches_the_section_and_the_key() -> None:
    assert _opens_requirement_array("project", "dependencies=[") is True
    assert _opens_requirement_array("project", "dependencies=foo=[") is True
    assert _opens_requirement_array("project", "dependencies = requests") is False
    assert _opens_requirement_array("project.optional-dependencies", "noequals [") is False
    assert _opens_requirement_array("other", "dependencies=[") is False
    assert _opens_requirement_array("project", "other=[") is False
    assert _opens_requirement_array("project.optional-dependencies", "extra=[") is True
    assert _opens_requirement_array("dependency-groups", "extra=[") is True


def test_poetry_section_and_skips_and_version() -> None:
    assert _poetry_section("tool.poetry.dependencies") is True
    assert _poetry_section("tool.poetry.group.dev.dependencies") is True
    assert _poetry_section("tool.poetry.group.dev") is False
    assert _poetry_section("other.dependencies") is False
    assert _poetry_skips("path = ../x") is True
    assert _poetry_skips("git = https://example.com/a.git") is True
    assert _poetry_skips("url = https://example.com/a") is True
    assert _poetry_skips('version = "1.2.3"') is False
    assert _poetry_version('{ path = "nope", version = "1.2.3" }') == "1.2.3"
    assert _poetry_version('"1.2.3"') == "1.2.3"
    assert _poetry_row("tool.poetry.dependencies", 'python = "^3.10"', 4) is None
    assert _poetry_row("tool.poetry.dependencies", 'rich = "1.2.3"', 5) == _Decl(
        "rich", "1.2.3", 5
    )


def test_quoted_value_reads_single_quotes() -> None:
    assert _quoted_value("'1.2.3'") == "1.2.3"
    assert _quoted_value('""') is None


def test_requirement_rejects_a_direct_reference_and_keeps_an_extra() -> None:
    assert _requirement("requests==1.2.3") == ("requests", "1.2.3")
    assert _requirement("name [extra]==1.0.0") == ("name", "1.0.0")
    assert _requirement("foo extra @ bar") is None
    assert _requirement("foo [https://x]==1.2.3") is None
    assert _requirement("") is None
    assert _requirement("-requests==1") is None
    assert _requirement("./rel==1") is None
    assert _requirement("/abs==1") is None


def test_spec_strips_one_bracket_and_rejects_a_direct_reference() -> None:
    assert _spec("[security]==1.2.3") == "==1.2.3"
    assert _spec("[]==1.0") == "==1.0"
    assert _spec("[foo] bar]==1.2.3") == "bar]==1.2.3"
    assert _spec("==1.2.3") == "==1.2.3"
    assert _spec("@1.0") is None
    assert _spec("https://example.com/pkg") is None
    assert _spec("[unclosed") is None
    assert _spec("[") is None


def test_requirement_declarations_strip_a_hash_comment() -> None:
    assert _requirement_declarations("requests==1.0.0#comment\n") == (
        _Decl("requests", "1.0.0", 1),
    )
    assert _requirement_declarations("requests==1.0.0 # note # more\n") == (
        _Decl("requests", "1.0.0", 1),
    )


def test_declarations_parse_requirements_txt_and_leave_other_names_to_python() -> None:
    pyproject = '[project]\ndependencies = [\n  "requests==1.0.0",\n]\n'

    assert _declarations("requests==1.2.3\n", "pypi", "requirements.txt") == (
        _Decl("requests", "1.2.3", 1),
    )
    assert _declarations("requests==1.2.3\n", "pypi", "notes.txt") == ()
    assert _declarations(pyproject, "pypi", "requirements.toml") == (
        _Decl("requests", "1.0.0", 3),
    )


def test_python_declarations_stop_at_the_array_and_ignore_comments() -> None:
    one_line = '[project]\ndependencies = ["flask==1.0.0"]\n"extra==2.0.0"\n'
    spanned = (
        "[project]\ndependencies = [\n  \"flask==1.0.0\",\n]\n\"extra==2.0.0\"\n"
    )
    between = (
        "[project]\ndependencies = [\n"
        '  "flask==1.0.0", # "extra==9.9.9" # tail\n]\n'
    )
    beside = (
        "[project]\ndependencies = [\n  \"flask==1.0.0\" # \"extra==9.9.9\"\n]\n"
    )
    early = '"early==1.0.0"\n[project]\ndependencies = [\n  "flask==1.0.0",\n]\n'

    assert _python_declarations(one_line) == (_Decl("flask", "1.0.0", 2),)
    assert _python_declarations(spanned) == (_Decl("flask", "1.0.0", 3),)
    assert _python_declarations(between) == (_Decl("flask", "1.0.0", 3),)
    assert _python_declarations(beside) == (_Decl("flask", "1.0.0", 3),)
    assert _python_declarations(early) == (_Decl("flask", "1.0.0", 4),)
    assert _python_declarations("requests==1.0.0\n") == ()


def test_excluded_strips_slashes_and_matches_a_path_part() -> None:
    assert _excluded("vendor/package.json", ("/vendor/",)) is True
    assert _excluded("Xvendor/package.json", ("Xvendor",)) is True
    assert _excluded("src/package.json", ("vendor",)) is False


def test_root_manifests_follow_the_index(tmp_path: Path) -> None:
    (tmp_path / "package.json").write_text("{}\n")
    (tmp_path / "pyproject.toml").write_text("[project]\n")
    (tmp_path / "requirements-dev.txt").write_text("pytest==8.0.0\n")
    (tmp_path / "requirements.txt").write_text("flask==1.0.0\n")

    assert _root_manifests(tmp_path, "npm") == (tmp_path / "package.json",)
    assert _root_manifests(tmp_path, "pypi") == (
        tmp_path / "pyproject.toml",
        tmp_path / "requirements-dev.txt",
        tmp_path / "requirements.txt",
    )

    empty = tmp_path / "empty"
    empty.mkdir()
    assert _root_manifests(empty, "npm") == ()


def test_manifests_walk_included_directories_and_skip_excluded_ones(tmp_path: Path) -> None:
    (tmp_path / "package.json").write_text("{}\n")
    (tmp_path / "pyproject.toml").write_text("[project]\n")
    (tmp_path / "requirements.txt").write_text("flask==1.0.0\n")
    (tmp_path / "notes.txt").write_text("not a manifest\n")
    src = tmp_path / "src" / "pkg"
    src.mkdir(parents=True)
    (src / "pyproject.toml").write_text("[project]\n")
    (src / "package.json").write_text("{}\n")
    vendor = tmp_path / "vendor" / "nested"
    vendor.mkdir(parents=True)
    (tmp_path / "vendor" / "pyproject.toml").write_text("[project]\n")
    (vendor / "package.json").write_text("{}\n")

    assert _manifests(tmp_path, "pypi", ("src",), ("vendor",)) == (
        tmp_path / "pyproject.toml",
        tmp_path / "requirements.txt",
        src / "pyproject.toml",
    )
    assert _manifests(tmp_path, "npm", ("src",), ("vendor",)) == (
        tmp_path / "package.json",
        src / "package.json",
    )


def test_keep_drops_a_directory_and_a_repeated_file(tmp_path: Path) -> None:
    found: list[Path] = []
    seen: set[Path] = set()
    src = tmp_path / "src"
    src.mkdir()
    path = tmp_path / "pyproject.toml"
    path.write_text("[project]\n")

    _keep(found, seen, tmp_path, src, ())
    _keep(found, seen, tmp_path, path, ())
    _keep(found, seen, tmp_path, path, ())

    assert found == [path]


def test_npm_locked_reads_shrinkwrap_dependencies(tmp_path: Path) -> None:
    manifest = tmp_path / "package.json"
    manifest.write_text("{}\n")
    (tmp_path / "npm-shrinkwrap.json").write_text(
        '{"dependencies": {"left-pad": {"version": "1.2.3"}}}\n'
    )

    assert _npm_locked(manifest, "left-pad") == "1.2.3"
    assert _npm_lock_file(tmp_path / "npm-shrinkwrap.json", "left-pad") == "1.2.3"


def test_python_locked_reads_each_lock_when_it_is_the_first_hit(tmp_path: Path) -> None:
    sub = tmp_path / "pkg"
    sub.mkdir()
    manifest = sub / "pyproject.toml"
    manifest.write_text("[project]\n")
    (sub / "poetry.lock").write_text(_lock("flask", "1.0.0"))
    assert _python_locked(tmp_path, manifest, "flask") == "1.0.0"

    (sub / "poetry.lock").unlink()
    (sub / "uv.lock").write_text(_lock("flask", "2.0.0"))
    assert _python_locked(tmp_path, manifest, "flask") == "2.0.0"

    (sub / "uv.lock").unlink()
    (tmp_path / "poetry.lock").write_text(_lock("flask", "3.0.0"))
    assert _python_locked(tmp_path, manifest, "flask") == "3.0.0"

    (tmp_path / "poetry.lock").unlink()
    (tmp_path / "uv.lock").write_text(_lock("flask", "4.0.0"))
    assert _python_locked(tmp_path, manifest, "flask") == "4.0.0"


def test_toml_lock_reads_the_version_that_belongs_to_the_name(tmp_path: Path) -> None:
    normal = tmp_path / "normal.lock"
    normal.write_text(
        "version = \"8.8.8\"\n[[package]]\nversion = \"9.9.9\"\n"
        "name = \"flask\"\nversion = \"1.0.0\"\n"
    )
    stolen = tmp_path / "stolen.lock"
    stolen.write_text(
        "[[package]]\nname = \"flask\"\n[[package]]\nversion = \"9.9.9\"\n"
        "name = \"other\"\nversion = \"1.0.0\"\n"
    )
    equals = tmp_path / "equals.lock"
    equals.write_text('[[package]]\nname = "fl=ask"\nversion = "1=2.3"\n')
    tight = tmp_path / "tight.lock"
    tight.write_text('[[package]]\nname="flask"\nversion="1.2.3"\n')

    assert _toml_lock(normal, "") is None
    assert _toml_lock(normal, "flask") == "1.0.0"
    assert _toml_lock(stolen, "flask") is None
    assert _toml_lock(stolen, "other") == "1.0.0"
    assert _toml_lock(equals, "fl=ask") == "1=2.3"
    assert _toml_lock(tight, "flask") == "1.2.3"


def test_git_show_passes_the_blob_args_and_an_empty_missing_file(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    seen: list[tuple[list[str], Path, bool]] = []

    def fake_run(args: list[str], *, cwd: Path, capture_output: bool, text: bool, check: bool):
        seen.append((list(args), cwd, check))
        if str(args[-1]).endswith("missing.txt"):
            return subprocess.CompletedProcess(
                args, 1, "", "fatal: path 'missing.txt' does not exist in 'main'"
            )
        if str(args[-1]).endswith("bad.txt"):
            return subprocess.CompletedProcess(args, 1, "", "fatal: bad revision")
        return subprocess.CompletedProcess(args, 0, "flask==1.0.0\n", "")

    monkeypatch.setattr("bob_quality.adapters.manifests.subprocess.run", fake_run)

    assert _git_show(tmp_path, "main", "pyproject.toml") == "flask==1.0.0\n"
    assert _git_show(tmp_path, "main", "missing.txt") == ""
    assert _git_show(tmp_path, "main", "bad.txt") is None
    assert seen == [
        (["git", "show", "main:pyproject.toml"], tmp_path, False),
        (["git", "show", "main:missing.txt"], tmp_path, False),
        (["git", "show", "main:bad.txt"], tmp_path, False),
    ]


def test_base_names_keep_npm_spelling_and_normalize_pypi(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    (repo / "package.json").write_text('{\n  "dependencies": {\n    "Left_Pad": "1.0.0"\n  }\n}\n')
    (repo / "pyproject.toml").write_text(
        '[project]\ndependencies = [\n  "Cool_Pkg==1.0.0",\n]\n'
    )
    _commit(repo, "base")

    assert _base_names(repo, "main", "package.json", "npm", "package.json") == {"Left_Pad"}
    assert _base_names(repo, "main", "pyproject.toml", "pypi", "pyproject.toml") == {"cool-pkg"}


def test_added_packages_skips_base_names_duplicates_and_lines_outside_the_diff(
    tmp_path: Path,
) -> None:
    repo = _repo(tmp_path)
    (repo / "pyproject.toml").write_text(
        '[project]\ndependencies = [\n  "Cool_Pkg==1.0.0",\n]\n'
    )
    _commit(repo, "base")
    _git(repo, "checkout", "-b", "head")
    (repo / "pyproject.toml").write_text(
        "[project]\n"
        "dependencies = [\n"
        '  "Cool_Pkg==2.0.0",\n'
        '  "Cool_Pkg==2.0.0",\n'
        '  "New_Pkg==1.2.3",\n'
        '  "New_Pkg==1.2.3",\n'
        '  "Flask==1.0.0",\n'
        "]\n"
    )
    _commit(repo, "head")

    found = added_packages(
        repo, "main", {"pyproject.toml": {3, 4, 5, 6}}, "pypi", (), ()
    )

    assert found == (AddedPackage("pypi", "new-pkg", "1.2.3", "pyproject.toml", 5),)


def test_added_packages_keeps_an_npm_name_that_the_base_did_not_normalize(
    tmp_path: Path,
) -> None:
    repo = _repo(tmp_path)
    (repo / "package.json").write_text(
        '{\n  "dependencies": {\n    "Left_Pad": "1.0.0"\n  }\n}\n'
    )
    _commit(repo, "base")
    _git(repo, "checkout", "-b", "head")
    (repo / "package.json").write_text(
        "{\n"
        '  "dependencies": {\n'
        '    "Left_Pad": "2.0.0",\n'
        '    "Right_Pad": "1.2.3"\n'
        "  }\n"
        "}\n"
    )
    _commit(repo, "head")

    found = added_packages(repo, "main", {"package.json": {3, 4}}, "npm", (), ())

    assert found == (AddedPackage("npm", "Right_Pad", "1.2.3", "package.json", 4),)


def test_added_packages_ignores_a_manifest_with_no_diff_entry(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    (repo / "README.md").write_text("base\n")
    _commit(repo, "base")
    _git(repo, "checkout", "-b", "head")
    (repo / "requirements.txt").write_text("added==1.0.0\n")
    _commit(repo, "head")

    assert added_packages(repo, "main", {}, "pypi", (), ()) == ()


def test_a_requirements_file_missing_from_base_counts_every_new_name(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    (repo / "README.md").write_text("base\n")
    _commit(repo, "base")
    _git(repo, "checkout", "-b", "head")
    (repo / "requirements.txt").write_text("XXXX\nadded==1.0.0\n")
    _commit(repo, "head")

    found = added_packages(repo, "main", {"requirements.txt": {1, 2}}, "pypi", (), ())

    assert found == (
        AddedPackage("pypi", "xxxx", None, "requirements.txt", 1),
        AddedPackage("pypi", "added", "1.0.0", "requirements.txt", 2),
    )


def _lock(name: str, version: str) -> str:
    return f'[[package]]\nname = "{name}"\nversion = "{version}"\n'


def _repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-b", "main")
    _git(repo, "config", "user.email", "bob-test@example.com")
    _git(repo, "config", "user.name", "bob-test")
    return repo


def _commit(repo: Path, message: str) -> None:
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", message)
