from pathlib import Path


def repo_relative(filename: str, root: Path) -> str | None:
    path = Path(filename)
    if not path.is_absolute() and ".." not in path.parts:
        return _plain(path.as_posix())
    if path.is_absolute():
        candidate = path
    else:
        # `root / absolute` equals the absolute path, so the join has to stay a string.
        candidate = Path(f"{root.as_posix()}/{path.as_posix()}")
    try:
        relative = candidate.resolve().relative_to(root.resolve())
    except ValueError:
        return None
    return _plain(relative.as_posix())


def _plain(text: str) -> str | None:
    if text == ".":
        return None
    return text
