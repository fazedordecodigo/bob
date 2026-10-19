"""bob_home (CT5, CT6)."""

from pathlib import Path

import pytest

from bob_quality.user_dirs import bob_home


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
