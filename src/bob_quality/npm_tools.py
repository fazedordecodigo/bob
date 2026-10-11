"""Invoca c8 e vitest pinados via npx. Não copia o código deles."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

from bob_quality.tools import ToolError

_NPM_PACKAGE = "bob-quality-tools"
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
NODE_MISSING = (
    "Node ausente: instale Node.js para medir TypeScript (c8 e vitest via npx)"
)
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

    Prefere quem já tem node_modules: a raiz do repo no desenvolvimento, o
    pacote instalado depois de `bob doctor --install`, ou o cache do usuário
    quando o diretório do pacote não é gravável.
    """
    matches = _plugin_packages()
    if not matches:
        raise ToolError(
            "package.json do plugin (bob-quality-tools) não encontrado; "
            "c8 e vitest ficam fixados nele"
        )
    installed = _first_with_modules(matches)
    if installed is not None:
        return installed
    return _cache_or_first(matches)


def _first_with_modules(matches: list[Path]) -> Path | None:
    for parent in matches:
        if (parent / "node_modules").is_dir():
            return parent
    return None


def _cache_or_first(matches: list[Path]) -> Path:
    cached = user_npm_cache()
    if _cache_ready(cached):
        return cached
    return matches[0]


def _cache_ready(cached: Path) -> bool:
    if not (cached / "node_modules").is_dir():
        return False
    return _is_plugin_manifest(cached / "package.json")


def install_npm_dependencies() -> int:
    """Roda `npm ci --prefix` no pacote instalado, ou num cache se ele não for gravável."""
    source = _install_source()
    if source is None:
        return 4
    return _npm_ci(_install_target(source))


def _install_source() -> Path | None:
    matches = _plugin_packages()
    if matches:
        return matches[0]
    print(
        "package.json do plugin (bob-quality-tools) não encontrado; "
        "c8 e vitest ficam fixados nele"
    )
    return None


def _install_target(source: Path) -> Path:
    if _can_write(source):
        return source
    return _materialize_cache(source)


def _npm_ci(target: Path) -> int:
    command = npm_ci_command(target)
    completed = subprocess.run(
        ["npm", "ci", "--prefix", str(target)],
        capture_output=True,
        text=True,
    )
    if completed.returncode == 0:
        return 0
    _print_npm_failure(command, completed)
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
    for parent in Path(__file__).resolve().parents:
        if _is_plugin_manifest(parent / "package.json"):
            matches.append(parent)
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
    try:
        probe = directory / ".bob-write-probe"
        probe.write_text("")
        probe.unlink()
    except OSError:
        return False
    return True


def _materialize_cache(source: Path) -> Path:
    cache = user_npm_cache()
    cache.mkdir(parents=True, exist_ok=True)
    _copy_manifests(source, cache)
    _copy_js(source / "js", cache / "js")
    return cache


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


def node_missing_message() -> str | None:
    if shutil.which("node") is None or shutil.which("npx") is None:
        return NODE_MISSING
    return None


def installed_npm_version(prefix: Path, package: str) -> str:
    pkg = prefix / "node_modules" / package / "package.json"
    if not pkg.is_file():
        raise ToolError(
            "dependências npm do plugin ausentes: " + npm_setup_hint(prefix)
        )
    try:
        return str(json.loads(pkg.read_text())["version"])
    except (json.JSONDecodeError, KeyError) as exc:
        raise ToolError(f"versão de {package} ilegível") from exc


def run_vitest_under_c8(cwd: Path, include: list[str], reports_dir: Path) -> int:
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
    for pattern in ("tests/**", "node_modules/**", "dist/**"):
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
    env = {key: value for key, value in os.environ.items() if not key.startswith("PYTEST_")}
    bindir = prefix / "node_modules" / ".bin"
    env["PATH"] = str(bindir) + os.pathsep + env.get("PATH", "")
    env["BOB_VITEST_SETUP"] = str(prefix / "js" / "flush-coverage.mjs")
    if user_config is not None:
        env["BOB_USER_VITEST_CONFIG"] = str(user_config)
        if user_config.suffix in {".ts", ".mts", ".cts"}:
            current = env.get("NODE_OPTIONS", "")
            flag = "--experimental-strip-types"
            if flag not in current.split():
                env["NODE_OPTIONS"] = (current + " " + flag).strip()
    completed = subprocess.run(
        args,
        cwd=cwd,
        capture_output=True,
        text=True,
        stdin=subprocess.DEVNULL,
        env=env,
    )
    if completed.returncode != 0 and not (reports_dir / "coverage-final.json").is_file():
        detail = (completed.stderr or completed.stdout or "c8/vitest falhou").strip()
        raise ToolError(detail)
    return completed.returncode


def _user_vitest_config(cwd: Path) -> Path | None:
    for name in _VITEST_CONFIG_NAMES:
        candidate = cwd / name
        if candidate.is_file():
            return candidate
    return None
