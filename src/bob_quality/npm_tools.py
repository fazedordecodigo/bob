"""Invoca c8 e vitest pinados via npx. Não copia o código deles."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from pathlib import Path

from bob_quality.messages import Language, Message, msg, render, t
from bob_quality.tools import ToolError

_NPM_PACKAGE = "bob-quality-tools"
_FILESYSTEM_DENIED = re.compile(r"\bcode (EACCES|EPERM|EROFS)\b")
_VITEST_CONFIG_NAMES = (
    "vitest.config.mjs",
    "vitest.config.js",
    "vitest.config.cjs",
    "vitest.config.mts",
    "vitest.config.ts",
    "vite.config.mjs",
    "vite.config.js",
    "vite.config.ts",
)
NODE_MISSING = msg("npm.node_missing")
_MANIFEST_MISSING = msg("npm.manifest_missing")
_VITEST_WRAPPER = """\
import { pathToFileURL } from "node:url";

const setup = process.env.BOB_VITEST_SETUP;
const userPath = process.env.BOB_USER_VITEST_CONFIG;
let user = {};
if (userPath) {
  const imported = await import(pathToFileURL(userPath).href);
  user = imported.default ?? imported;
}
const test = { ...(user.test ?? {}) };
const setupFiles = Array.isArray(test.setupFiles)
  ? [...test.setupFiles]
  : test.setupFiles
    ? [test.setupFiles]
    : [];
if (setup && !setupFiles.includes(setup)) setupFiles.push(setup);
test.setupFiles = setupFiles;
export default { ...user, test };
"""


def npm_ci_command(prefix: Path) -> str:
    return f"npm ci --prefix {prefix}"


def npm_setup_hint(prefix: Path) -> str:
    """Comando para instalar as deps npm. Diretório travado: `bob doctor --install`."""
    if _can_write(prefix):
        return npm_ci_command(prefix)
    return "bob doctor --install"


def npm_prefix() -> Path:
    """Raiz do package.json fixado do plugin (não o repo alvo).

    Prefere o cache do usuário instalado com o mesmo package.json do pacote
    (o `bob doctor --install` só o cria quando o npm não escreve no pacote).
    Depois, quem já tem node_modules: a raiz do repo no desenvolvimento ou o
    pacote instalado.
    """
    matches = _plugin_packages()
    if not matches:
        raise ToolError(_MANIFEST_MISSING)
    cached = user_npm_cache()
    if _cache_ready(cached, matches[0]):
        return cached
    installed = _first_with_modules(matches)
    if installed is not None:
        return installed
    return matches[0]


def _first_with_modules(matches: list[Path]) -> Path | None:
    for parent in matches:
        if (parent / "node_modules").is_dir():
            return parent
    return None


def _cache_ready(cached: Path, source: Path) -> bool:
    if not (cached / "node_modules").is_dir():
        return False
    return _load_manifest(cached / "package.json") == _load_manifest(source / "package.json")


def install_npm_dependencies(lang: Language) -> int:
    """Roda `npm ci --prefix` no pacote; se o sistema de arquivos negar, no cache do usuário."""
    source = _install_source(lang)
    if source is None:
        return 4
    completed = _run_npm_ci(source)
    denied = _FILESYSTEM_DENIED.search(completed.stderr)
    if denied:
        return _install_in_cache(source, denied.group(1), lang)
    return _npm_verdict(source, completed)


def _install_in_cache(source: Path, code: str, lang: Language) -> int:
    cache = user_npm_cache()
    command = npm_ci_command(source)
    print(t(lang, "npm.cache_fallback", command=command, code=code, cache=cache))
    try:
        _materialize_cache(source, cache)
    except OSError as exc:
        print(t(lang, "npm.cache_unavailable", cache=cache, detail=exc.strerror))
        return 4
    return _npm_verdict(cache, _run_npm_ci(cache))


def _install_source(lang: Language) -> Path | None:
    matches = _plugin_packages()
    if matches:
        return matches[0]
    print(render(_MANIFEST_MISSING, lang))
    return None


def _run_npm_ci(target: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["npm", "ci", "--prefix", str(target)],
        capture_output=True,
        text=True,
    )


def _npm_verdict(target: Path, completed: subprocess.CompletedProcess[str]) -> int:
    if completed.returncode == 0:
        return 0
    _print_npm_failure(npm_ci_command(target), completed)
    return 4


def _print_npm_failure(command: str, completed: subprocess.CompletedProcess[str]) -> None:
    detail = _failure_detail(completed)
    if detail:
        print(f"{command}\n{detail}")
        return
    print(command)


def _failure_detail(completed: subprocess.CompletedProcess[str]) -> str:
    if completed.stderr:
        return completed.stderr.strip()
    if completed.stdout:
        return completed.stdout.strip()
    return ""


def user_npm_cache() -> Path:
    base = os.environ.get("XDG_CACHE_HOME")
    root = Path(base) if base else Path.home() / ".cache"
    return root / "bob-quality"


def _plugin_packages() -> list[Path]:
    matches: list[Path] = []
    seen: set[Path] = set()
    for parent in Path(os.path.abspath(__file__)).parents:
        manifest = parent / "package.json"
        if not _is_plugin_manifest(manifest):
            continue
        home = manifest.resolve().parent if manifest.is_symlink() else parent
        if home in seen:
            continue
        seen.add(home)
        matches.append(home)
    return matches


def _is_plugin_manifest(path: Path) -> bool:
    data = _load_manifest(path)
    return data is not None and data.get("name") == _NPM_PACKAGE


def _load_manifest(path: Path) -> dict[str, object] | None:
    if not path.is_file():
        return None
    return _parse_manifest(path)


def _parse_manifest(path: Path) -> dict[str, object] | None:
    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError:
        return None
    if isinstance(data, dict):
        return data
    return None


def _can_write(directory: Path) -> bool:
    return os.access(directory, os.W_OK)


def _materialize_cache(source: Path, cache: Path) -> None:
    cache.mkdir(parents=True, exist_ok=True)
    _copy_manifests(source, cache)
    _copy_js(source / "js", cache / "js")


def _copy_manifests(source: Path, cache: Path) -> None:
    shutil.copy2(source / "package.json", cache / "package.json")
    lock = source / "package-lock.json"
    if lock.is_file():
        shutil.copy2(lock, cache / "package-lock.json")


def _copy_js(src: Path, dst: Path) -> None:
    if dst.exists():
        shutil.rmtree(dst)
    if src.is_dir():
        shutil.copytree(src, dst)


def node_missing_message() -> Message | None:
    if shutil.which("node") is None or shutil.which("npx") is None:
        return NODE_MISSING
    return None


def installed_npm_version(prefix: Path, package: str) -> str:
    pkg = prefix / "node_modules" / package / "package.json"
    if not pkg.is_file():
        raise ToolError(msg("npm.deps_missing", hint=npm_setup_hint(prefix)))
    try:
        return str(json.loads(pkg.read_text())["version"])
    except (json.JSONDecodeError, KeyError) as exc:
        raise ToolError(msg("npm.unreadable_version", package=package)) from exc


def run_vitest_under_c8(
    cwd: Path,
    include: list[str],
    reports_dir: Path,
    exclude: list[str],
) -> int:
    """Roda vitest sob c8 via npx e grava coverage-final.json. Devolve o exit do vitest."""
    missing = node_missing_message()
    if missing:
        raise ToolError(missing)
    prefix = npm_prefix()
    installed_npm_version(prefix, "c8")
    installed_npm_version(prefix, "vitest")
    reports_dir.mkdir(parents=True, exist_ok=True)
    wrapper = reports_dir.parent / "vitest.bob.config.mjs"
    wrapper.write_text(_VITEST_WRAPPER)
    user_config = _user_vitest_config(cwd)
    completed = subprocess.run(
        _c8_argv(prefix, cwd, include, exclude, reports_dir, wrapper),
        cwd=cwd,
        capture_output=True,
        text=True,
        stdin=subprocess.DEVNULL,
        env=_vitest_env(prefix, user_config),
    )
    _raise_if_c8_failed(completed, reports_dir)
    return completed.returncode


def _c8_argv(
    prefix: Path,
    cwd: Path,
    include: list[str],
    exclude: list[str],
    reports_dir: Path,
    wrapper: Path,
) -> list[str]:
    args = [
        "npx",
        "--prefix",
        str(prefix),
        "c8",
        "--reporter=json",
        "--reports-dir",
        str(reports_dir),
        "--all",
    ]
    for pattern in _c8_exclude_patterns(exclude):
        args.extend(["--exclude", pattern])
    for path in include or ["src"]:
        args.extend(["--include", f"{path}/**"])
    args.extend(
        [
            "vitest",
            "run",
            "--root",
            str(cwd),
            "--config",
            str(wrapper),
            "--reporter=dot",
        ]
    )
    return args


def _vitest_env(prefix: Path, user_config: Path | None) -> dict[str, str]:
    env = {key: value for key, value in os.environ.items() if not key.startswith("PYTEST_")}
    env["BOB_VITEST_SETUP"] = str(prefix / "js" / "flush-coverage.mjs")
    if user_config is None:
        return env
    env["BOB_USER_VITEST_CONFIG"] = str(user_config)
    _enable_strip_types(env, user_config)
    return env


_STRIP_TYPES_FLAG = "--experimental-strip-types"
_TYPESCRIPT_CONFIG_SUFFIXES = (".ts", ".mts")


def _enable_strip_types(env: dict[str, str], user_config: Path) -> None:
    if not _needs_strip_types(user_config, env):
        return
    current = env.get("NODE_OPTIONS", "")
    env["NODE_OPTIONS"] = (current + " " + _STRIP_TYPES_FLAG).strip()


def _needs_strip_types(user_config: Path, env: dict[str, str]) -> bool:
    raw = env.get("NODE_OPTIONS")
    options = raw.split() if isinstance(raw, str) else []
    return (
        user_config.suffix in _TYPESCRIPT_CONFIG_SUFFIXES
        and _STRIP_TYPES_FLAG not in options
    )


def _raise_if_c8_failed(completed: subprocess.CompletedProcess[str], reports_dir: Path) -> None:
    if completed.returncode == 0 or (reports_dir / "coverage-final.json").is_file():
        return
    raw = completed.stderr or completed.stdout
    raise ToolError(raw.strip() if raw else msg("npm.c8_failed"))


def _c8_exclude_patterns(exclude: list[str]) -> list[str]:
    """`paths.exclude` lista diretórios; o c8 recebe o glob correspondente."""
    return [f"{pattern}/**" for pattern in exclude]


def _user_vitest_config(cwd: Path) -> Path | None:
    for name in _VITEST_CONFIG_NAMES:
        candidate = cwd / name
        if candidate.is_file():
            return candidate
    return None
