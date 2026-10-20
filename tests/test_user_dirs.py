"""bob_home (CT5, CT6) e locate_binary (CT8, ADR 0019)."""

import shutil
from pathlib import Path

import pytest

from bob_quality.user_dirs import bob_home, locate_binary


def test_default_is_under_home_local_share(monkeypatch: pytest.MonkeyPatch) -> None:
    home = bob_home({"HOME": "/h"})
    assert home.root == Path("/h/.local/share/bob-quality")
    assert home.versions == home.root / "versions"
    assert home.current == home.root / "current"
    assert home.bin == home.root / "bin"
    assert home.bin_bob == home.root / "bin" / "bob"
    assert home.tools == home.root / "tools"
    monkeypatch.setattr(Path, "home", lambda: Path("/from-home"))
    assert bob_home({}).root == Path("/from-home/.local/share/bob-quality")
    assert bob_home({"HOME": ""}).root == Path("/from-home/.local/share/bob-quality")


def test_absolute_xdg_data_home_is_used() -> None:
    assert bob_home({"HOME": "/h", "XDG_DATA_HOME": "/x"}).root == Path("/x/bob-quality")


def test_relative_xdg_data_home_is_ignored() -> None:
    root = bob_home({"HOME": "/h", "XDG_DATA_HOME": "rel"}).root
    assert root == Path("/h/.local/share/bob-quality")


def test_bob_home_wins_over_xdg() -> None:
    env = {"HOME": "/h", "XDG_DATA_HOME": "/x", "BOB_HOME": "/b"}
    assert bob_home(env).root == Path("/b")


def test_empty_values_count_as_unset() -> None:
    env = {"HOME": "/h", "XDG_DATA_HOME": "", "BOB_HOME": ""}
    assert bob_home(env).root == Path("/h/.local/share/bob-quality")


def test_relative_bob_home_is_a_value_error() -> None:
    with pytest.raises(ValueError) as caught:
        bob_home({"HOME": "/h", "BOB_HOME": "rel/b"})
    assert str(caught.value) == "rel/b"


def test_bob_home_reads_os_environ_by_default(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("BOB_HOME", str(tmp_path))
    assert bob_home().root == tmp_path


def _script(path: Path, mode: int = 0o755) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("#!/bin/sh\n")
    path.chmod(mode)


def test_locate_binary_prefers_bob_home_bin(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    home_bin = tmp_path / "bh" / "bin"
    _script(home_bin / "tool")
    path_dir = tmp_path / "path"
    _script(path_dir / "tool")
    monkeypatch.setenv("PATH", str(path_dir))
    found = locate_binary("tool", {"BOB_HOME": str(tmp_path / "bh")})
    assert found == str(home_bin / "tool")


def test_locate_binary_follows_a_link_without_resolving_it(
    tmp_path: Path,
) -> None:
    root = tmp_path / "bh"
    binary = root / "tools" / "gitleaks" / "8.30.1" / "gitleaks"
    _script(binary)
    link = root / "bin" / "gitleaks"
    link.parent.mkdir()
    link.symlink_to(Path("..") / "tools" / "gitleaks" / "8.30.1" / "gitleaks")
    found = locate_binary("gitleaks", {"BOB_HOME": str(root)})
    assert found == str(root / "bin" / "gitleaks")


@pytest.mark.parametrize(
    "kind",
    ["absent", "not_executable", "directory", "broken_link", "not_on_path"],
)
def test_locate_binary_falls_back_to_the_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, kind: str
) -> None:
    home_bin = tmp_path / "bh" / "bin"
    home_bin.mkdir(parents=True)
    tool = home_bin / "tool"
    if kind == "not_executable":
        _script(tool, 0o644)
    elif kind == "directory":
        tool.mkdir()
    elif kind == "broken_link":
        tool.symlink_to("missing")
    path_dir = tmp_path / "path"
    path_dir.mkdir()
    expected: str | None = None
    if kind != "not_on_path":
        path_tool = path_dir / "tool"
        _script(path_tool)
        expected = str(path_tool)
    monkeypatch.setenv("PATH", str(path_dir))
    assert locate_binary("tool", {"BOB_HOME": str(tmp_path / "bh")}) == expected


def test_locate_binary_with_relative_bob_home_uses_the_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path_dir = tmp_path / "path"
    _script(path_dir / "tool")
    monkeypatch.setenv("PATH", str(path_dir))
    assert locate_binary("tool", {"BOB_HOME": "rel"}) == shutil.which("tool")


def test_locate_binary_reads_os_environ_by_default(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    home_bin = tmp_path / "bh" / "bin"
    _script(home_bin / "tool")
    monkeypatch.setenv("BOB_HOME", str(tmp_path / "bh"))
    assert locate_binary("tool") == str(home_bin / "tool")
