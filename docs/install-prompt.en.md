# Install bob with your AI agent

> Alternative path. The main path is the install.sh one-liner; if they differ, the one-liner wins.

Paste this whole file into your AI agent, at the root of the project.

## Rules

```text
You are going to install bob (https://github.com/fazedordecodigo/bob) in this project, without install.sh. Rules:
1. Never use sudo.
2. Do not download or run install.sh. Do not clone the bob repository. Do not install an agent plugin.
3. Never skip or change a sha256 check.
4. Run the blocks in order, at the project root, one block per shell command, without editing any block. Each block is independent; the state lives in ${TMPDIR:-/tmp}/bob-install-<uid>.
5. After the "plataforma" step, run only the blocks with platform=all, with your system (linux or darwin) or with the platform it printed.
6. If a block exits with a code other than 0: stop. Show the human the full output of the block. Do not try to work around it, do not try another path.
7. At the end, paste the full output of the "setup" and "verificação" steps.
8. For bob messages in pt-BR, run the "setup" and "verificação" steps with BOB_LANG=pt-BR.
```

## 1. projeto

```sh bob-step=projeto platform=all
set -eu
fail() { printf 'bob-prompt: %s\n' "$*" >&2; exit 4; }
case "${XDG_DATA_HOME:-}" in /*) D="$XDG_DATA_HOME" ;; *) D="$HOME/.local/share" ;; esac
BOB_HOME="${BOB_HOME:-$D/bob-quality}"
case "$BOB_HOME" in /*) ;; *) fail "launcher: BOB_HOME=$BOB_HOME must be absolute" ;; esac
W="${TMPDIR:-/tmp}/bob-install-$(id -u)"
command -v git >/dev/null 2>&1 || fail "projeto: git not found; install git and run again"
top=$(git rev-parse --show-toplevel 2>/dev/null) || fail "projeto: $(pwd -P) is not the root of a git repository; run in the project root"
[ "$top" = "$(pwd -P)" ] || fail "projeto: $(pwd -P) is not the root of a git repository; run in the project root"
rm -rf "$W" && mkdir -p "$W" && pwd -P > "$W/project"
echo "bob-prompt: projeto: ok"
```

## 2. plataforma

```sh bob-step=plataforma platform=all
set -eu
fail() { printf 'bob-prompt: %s\n' "$*" >&2; exit 4; }
case "${XDG_DATA_HOME:-}" in /*) D="$XDG_DATA_HOME" ;; *) D="$HOME/.local/share" ;; esac
BOB_HOME="${BOB_HOME:-$D/bob-quality}"
case "$BOB_HOME" in /*) ;; *) fail "launcher: BOB_HOME=$BOB_HOME must be absolute" ;; esac
W="${TMPDIR:-/tmp}/bob-install-$(id -u)"
s=$(uname -s); m=$(uname -m)
case "$s/$m" in
  Linux/x86_64|Linux/amd64) p=linux-x64 ;;
  Linux/aarch64|Linux/arm64) p=linux-arm64 ;;
  Darwin/x86_64) p=darwin-x64 ;;
  Darwin/arm64) p=darwin-arm64 ;;
  *) fail "plataforma: $s/$m is not supported; supported: Linux and macOS, x64 and arm64" ;;
esac
printf '%s\n' "$p" > "$W/platform"
echo "bob-prompt: plataforma: $p"
```

## 3. python

```sh bob-step=python platform=all
set -eu
fail() { printf 'bob-prompt: %s\n' "$*" >&2; exit 4; }
case "${XDG_DATA_HOME:-}" in /*) D="$XDG_DATA_HOME" ;; *) D="$HOME/.local/share" ;; esac
BOB_HOME="${BOB_HOME:-$D/bob-quality}"
case "$BOB_HOME" in /*) ;; *) fail "launcher: BOB_HOME=$BOB_HOME must be absolute" ;; esac
W="${TMPDIR:-/tmp}/bob-install-$(id -u)"
command -v python3 >/dev/null 2>&1 || fail "python: python3 not found; install Python 3.10 or newer"
python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)' || fail "python: found $(python3 -c 'import platform; print(platform.python_version())'), required >=3.10"
python3 -c 'import venv, ensurepip' 2>/dev/null || fail "python: the venv module is not available; on Ubuntu, install python3-venv"
echo "bob-prompt: python: ok"
```

## 4. node

```sh bob-step=node platform=all
set -eu
fail() { printf 'bob-prompt: %s\n' "$*" >&2; exit 4; }
case "${XDG_DATA_HOME:-}" in /*) D="$XDG_DATA_HOME" ;; *) D="$HOME/.local/share" ;; esac
BOB_HOME="${BOB_HOME:-$D/bob-quality}"
case "$BOB_HOME" in /*) ;; *) fail "launcher: BOB_HOME=$BOB_HOME must be absolute" ;; esac
W="${TMPDIR:-/tmp}/bob-install-$(id -u)"
# node: >=22.18.0 <23
command -v node >/dev/null 2>&1 || fail "node: node not found; install Node >=22.18.0 <23"
command -v npm >/dev/null 2>&1 || fail "node: npm not found; install npm with Node"
v=$(node --version)
printf '%s\n' "$v" | grep -Eq '^v[0-9]+\.[0-9]+\.[0-9]+$' || fail "node: found $v, required >=22.18.0 <23"
python3 -c 'import sys; v = tuple(int(x) for x in sys.argv[1][1:].split(".")); sys.exit(0 if (22, 18, 0) <= v < (23,) else 1)' "$v" || fail "node: found $v, required >=22.18.0 <23"
echo "bob-prompt: node: ok"
```

## 5. ferramentas

```sh bob-step=ferramentas platform=linux
set -eu
fail() { printf 'bob-prompt: %s\n' "$*" >&2; exit 4; }
case "${XDG_DATA_HOME:-}" in /*) D="$XDG_DATA_HOME" ;; *) D="$HOME/.local/share" ;; esac
BOB_HOME="${BOB_HOME:-$D/bob-quality}"
case "$BOB_HOME" in /*) ;; *) fail "launcher: BOB_HOME=$BOB_HOME must be absolute" ;; esac
W="${TMPDIR:-/tmp}/bob-install-$(id -u)"
command -v curl >/dev/null 2>&1 || fail "ferramentas: curl not found; install curl and run again"
command -v sha256sum >/dev/null 2>&1 || fail "ferramentas: sha256sum not found; install coreutils and run again"
echo "bob-prompt: ferramentas: ok"
```

```sh bob-step=ferramentas platform=darwin
set -eu
fail() { printf 'bob-prompt: %s\n' "$*" >&2; exit 4; }
case "${XDG_DATA_HOME:-}" in /*) D="$XDG_DATA_HOME" ;; *) D="$HOME/.local/share" ;; esac
BOB_HOME="${BOB_HOME:-$D/bob-quality}"
case "$BOB_HOME" in /*) ;; *) fail "launcher: BOB_HOME=$BOB_HOME must be absolute" ;; esac
W="${TMPDIR:-/tmp}/bob-install-$(id -u)"
command -v curl >/dev/null 2>&1 || fail "ferramentas: curl not found; install curl and run again"
command -v shasum >/dev/null 2>&1 || fail "ferramentas: shasum not found; install it and run again"
echo "bob-prompt: ferramentas: ok"
```

## 6. versão

```sh bob-step=versão platform=all
set -eu
fail() { printf 'bob-prompt: %s\n' "$*" >&2; exit 4; }
case "${XDG_DATA_HOME:-}" in /*) D="$XDG_DATA_HOME" ;; *) D="$HOME/.local/share" ;; esac
BOB_HOME="${BOB_HOME:-$D/bob-quality}"
case "$BOB_HOME" in /*) ;; *) fail "launcher: BOB_HOME=$BOB_HOME must be absolute" ;; esac
W="${TMPDIR:-/tmp}/bob-install-$(id -u)"
if [ -n "${BOB_RELEASES_URL:-}" ]; then
  R=${BOB_RELEASES_URL%/}
  case "$R" in https://*|http://127.0.0.1|http://127.0.0.1[:/]*|http://localhost|http://localhost[:/]*) ;; *) fail "versão: BOB_RELEASES_URL=$R is not allowed (https, or http only on 127.0.0.1/localhost)" ;; esac
  API="$R/api/releases/latest"; DL="$R/download"
else
  API="https://api.github.com/repos/fazedordecodigo/bob/releases/latest"; DL="https://github.com/fazedordecodigo/bob/releases/download"
fi
if [ -n "${BOB_VERSION:-}" ]; then
  V=$BOB_VERSION
else
  V=$(curl -fsSL --connect-timeout 15 --max-time 300 --retry 2 -H 'Accept: application/vnd.github+json' "$API" | python3 -c 'import json, sys; print(json.load(sys.stdin)["tag_name"])') || fail "versão: could not read the latest release; try again later"
fi
printf '%s\n' "$V" | grep -Eq '^v[0-9]+\.[0-9]+\.[0-9]+$' || fail "versão: $V is not a valid tag (vX.Y.Z)"
printf '%s\n' "$V" > "$W/version"
printf '%s\n' "$DL" > "$W/dl"
echo "bob-prompt: versão: $V"
```

## 7. download

```sh bob-step=download platform=all
set -eu
fail() { printf 'bob-prompt: %s\n' "$*" >&2; exit 4; }
case "${XDG_DATA_HOME:-}" in /*) D="$XDG_DATA_HOME" ;; *) D="$HOME/.local/share" ;; esac
BOB_HOME="${BOB_HOME:-$D/bob-quality}"
case "$BOB_HOME" in /*) ;; *) fail "launcher: BOB_HOME=$BOB_HOME must be absolute" ;; esac
W="${TMPDIR:-/tmp}/bob-install-$(id -u)"
V=$(cat "$W/version"); DL=$(cat "$W/dl"); WHL="bob_quality-${V#v}-py3-none-any.whl"
for f in "$WHL" SHA256SUMS; do
  curl -fsSL --connect-timeout 15 --max-time 300 --retry 2 -o "$W/$f" "$DL/$V/$f" || fail "download: $DL/$V/$f failed; check the network and try again"
done
echo "bob-prompt: download: ok"
```

## 8. integridade

```sh bob-step=integridade platform=linux
set -eu
fail() { printf 'bob-prompt: %s\n' "$*" >&2; exit 4; }
case "${XDG_DATA_HOME:-}" in /*) D="$XDG_DATA_HOME" ;; *) D="$HOME/.local/share" ;; esac
BOB_HOME="${BOB_HOME:-$D/bob-quality}"
case "$BOB_HOME" in /*) ;; *) fail "launcher: BOB_HOME=$BOB_HOME must be absolute" ;; esac
W="${TMPDIR:-/tmp}/bob-install-$(id -u)"
V=$(cat "$W/version"); WHL="bob_quality-${V#v}-py3-none-any.whl"
want=$(awk -v f="$WHL" '$2 == f { print $1 }' "$W/SHA256SUMS")
got=$(sha256sum "$W/$WHL" | awk '{ print $1 }')
[ -n "$want" ] && [ "$want" = "$got" ] || fail "integridade: the sha256 of $WHL does not match; nothing was installed"
printf '%s\n' "$got" > "$W/wheel.sha256"
echo "bob-prompt: integridade: ok"
```

```sh bob-step=integridade platform=darwin
set -eu
fail() { printf 'bob-prompt: %s\n' "$*" >&2; exit 4; }
case "${XDG_DATA_HOME:-}" in /*) D="$XDG_DATA_HOME" ;; *) D="$HOME/.local/share" ;; esac
BOB_HOME="${BOB_HOME:-$D/bob-quality}"
case "$BOB_HOME" in /*) ;; *) fail "launcher: BOB_HOME=$BOB_HOME must be absolute" ;; esac
W="${TMPDIR:-/tmp}/bob-install-$(id -u)"
V=$(cat "$W/version"); WHL="bob_quality-${V#v}-py3-none-any.whl"
want=$(awk -v f="$WHL" '$2 == f { print $1 }' "$W/SHA256SUMS")
got=$(shasum -a 256 "$W/$WHL" | awk '{ print $1 }')
[ -n "$want" ] && [ "$want" = "$got" ] || fail "integridade: the sha256 of $WHL does not match; nothing was installed"
printf '%s\n' "$got" > "$W/wheel.sha256"
echo "bob-prompt: integridade: ok"
```

## 9. pacote

```sh bob-step=pacote platform=all
set -eu
fail() { printf 'bob-prompt: %s\n' "$*" >&2; exit 4; }
case "${XDG_DATA_HOME:-}" in /*) D="$XDG_DATA_HOME" ;; *) D="$HOME/.local/share" ;; esac
BOB_HOME="${BOB_HOME:-$D/bob-quality}"
case "$BOB_HOME" in /*) ;; *) fail "launcher: BOB_HOME=$BOB_HOME must be absolute" ;; esac
W="${TMPDIR:-/tmp}/bob-install-$(id -u)"
V=$(cat "$W/version"); X=${V#v}; WHL="bob_quality-$X-py3-none-any.whl"
H=$(cat "$W/wheel.sha256"); VD="$BOB_HOME/versions/$X"
if [ -f "$VD/.complete" ] && [ "$(cat "$VD/.complete")" = "$H" ]; then
  echo "bob-prompt: pacote: ok (reused)"
else
  rm -rf "$VD" && mkdir -p "$VD"
  { python3 -m venv "$VD/venv" && "$VD/venv/bin/pip" install --disable-pip-version-check --no-input "$W/$WHL"; } || { rm -rf "$VD"; fail "pacote: pip failed; see the output above and try again"; }
  printf '%s\n' "$H" > "$VD/.complete"
  echo "bob-prompt: pacote: ok"
fi
```

## 10. launcher

```sh bob-step=launcher platform=all
set -eu
fail() { printf 'bob-prompt: %s\n' "$*" >&2; exit 4; }
case "${XDG_DATA_HOME:-}" in /*) D="$XDG_DATA_HOME" ;; *) D="$HOME/.local/share" ;; esac
BOB_HOME="${BOB_HOME:-$D/bob-quality}"
case "$BOB_HOME" in /*) ;; *) fail "launcher: BOB_HOME=$BOB_HOME must be absolute" ;; esac
W="${TMPDIR:-/tmp}/bob-install-$(id -u)"
V=$(cat "$W/version"); X=${V#v}; L="$HOME/.local/bin/bob"
mkdir -p "$BOB_HOME/bin" "$HOME/.local/bin" || fail "launcher: could not create $BOB_HOME/bin or $HOME/.local/bin"
rm -f "$BOB_HOME/current.tmp"
ln -s "versions/$X" "$BOB_HOME/current.tmp" || fail "launcher: could not create $BOB_HOME/current.tmp"
"$BOB_HOME/versions/$X/venv/bin/python" -c 'import os, sys; os.replace(sys.argv[1], sys.argv[2])' "$BOB_HOME/current.tmp" "$BOB_HOME/current" || fail "launcher: could not create $BOB_HOME/current"
ln -sfn ../current/venv/bin/bob "$BOB_HOME/bin/bob" || fail "launcher: could not create $BOB_HOME/bin/bob"
if [ -L "$L" ] && [ "$(readlink "$L")" = "$BOB_HOME/bin/bob" ]; then
  :
elif [ -e "$L" ] || [ -L "$L" ]; then
  echo "bob-prompt: launcher: warning: $L already exists and is not bob's; left as is"
else
  ln -s "$BOB_HOME/bin/bob" "$L" || fail "launcher: could not create $L"
fi
echo "bob-prompt: launcher: ok"
```

## 11. gitleaks

```sh bob-step=gitleaks platform=linux-x64
set -eu
fail() { printf 'bob-prompt: %s\n' "$*" >&2; exit 4; }
case "${XDG_DATA_HOME:-}" in /*) D="$XDG_DATA_HOME" ;; *) D="$HOME/.local/share" ;; esac
BOB_HOME="${BOB_HOME:-$D/bob-quality}"
case "$BOB_HOME" in /*) ;; *) fail "launcher: BOB_HOME=$BOB_HOME must be absolute" ;; esac
W="${TMPDIR:-/tmp}/bob-install-$(id -u)"
A=gitleaks_8.30.1_linux_x64.tar.gz
S=551f6fc83ea457d62a0d98237cbad105af8d557003051f41f3e7ca7b3f2470eb
G="$BOB_HOME/tools/gitleaks/8.30.1"
GB=${BOB_GITLEAKS_BASE_URL:-https://github.com/gitleaks/gitleaks/releases/download/v8.30.1}; GB=${GB%/}
case "$GB" in https://*|http://127.0.0.1|http://127.0.0.1[:/]*|http://localhost|http://localhost[:/]*) ;; *) fail "gitleaks: BOB_GITLEAKS_BASE_URL=$GB is not allowed" ;; esac
if [ -x "$BOB_HOME/bin/gitleaks" ] && "$BOB_HOME/bin/gitleaks" --version 2>/dev/null | grep -qF 8.30.1; then
  echo "bob-prompt: gitleaks: ok (reused)"
else
  curl -fsSL --connect-timeout 15 --max-time 300 --retry 2 -o "$W/$A" "$GB/$A" || fail "gitleaks: download of $GB/$A failed; check the network and try again"
  [ "$(sha256sum "$W/$A" | awk '{ print $1 }')" = "$S" ] || fail "gitleaks: the sha256 of $A does not match; nothing was installed"
  rm -rf "$W/gl" && mkdir "$W/gl"
  tar -xzf "$W/$A" -C "$W/gl" gitleaks 2>/dev/null || fail "gitleaks: $A does not have the expected gitleaks binary; nothing was installed"
  [ -f "$W/gl/gitleaks" ] && [ ! -L "$W/gl/gitleaks" ] || fail "gitleaks: $A does not have the expected gitleaks binary; nothing was installed"
  mkdir -p "$G" "$BOB_HOME/bin"
  cp "$W/gl/gitleaks" "$G/gitleaks.tmp" && chmod 0755 "$G/gitleaks.tmp" && mv -f "$G/gitleaks.tmp" "$G/gitleaks"
  ln -sfn ../tools/gitleaks/8.30.1/gitleaks "$BOB_HOME/bin/gitleaks"
  echo "bob-prompt: gitleaks: ok"
fi
```

```sh bob-step=gitleaks platform=linux-arm64
set -eu
fail() { printf 'bob-prompt: %s\n' "$*" >&2; exit 4; }
case "${XDG_DATA_HOME:-}" in /*) D="$XDG_DATA_HOME" ;; *) D="$HOME/.local/share" ;; esac
BOB_HOME="${BOB_HOME:-$D/bob-quality}"
case "$BOB_HOME" in /*) ;; *) fail "launcher: BOB_HOME=$BOB_HOME must be absolute" ;; esac
W="${TMPDIR:-/tmp}/bob-install-$(id -u)"
A=gitleaks_8.30.1_linux_arm64.tar.gz
S=e4a487ee7ccd7d3a7f7ec08657610aa3606637dab924210b3aee62570fb4b080
G="$BOB_HOME/tools/gitleaks/8.30.1"
GB=${BOB_GITLEAKS_BASE_URL:-https://github.com/gitleaks/gitleaks/releases/download/v8.30.1}; GB=${GB%/}
case "$GB" in https://*|http://127.0.0.1|http://127.0.0.1[:/]*|http://localhost|http://localhost[:/]*) ;; *) fail "gitleaks: BOB_GITLEAKS_BASE_URL=$GB is not allowed" ;; esac
if [ -x "$BOB_HOME/bin/gitleaks" ] && "$BOB_HOME/bin/gitleaks" --version 2>/dev/null | grep -qF 8.30.1; then
  echo "bob-prompt: gitleaks: ok (reused)"
else
  curl -fsSL --connect-timeout 15 --max-time 300 --retry 2 -o "$W/$A" "$GB/$A" || fail "gitleaks: download of $GB/$A failed; check the network and try again"
  [ "$(sha256sum "$W/$A" | awk '{ print $1 }')" = "$S" ] || fail "gitleaks: the sha256 of $A does not match; nothing was installed"
  rm -rf "$W/gl" && mkdir "$W/gl"
  tar -xzf "$W/$A" -C "$W/gl" gitleaks 2>/dev/null || fail "gitleaks: $A does not have the expected gitleaks binary; nothing was installed"
  [ -f "$W/gl/gitleaks" ] && [ ! -L "$W/gl/gitleaks" ] || fail "gitleaks: $A does not have the expected gitleaks binary; nothing was installed"
  mkdir -p "$G" "$BOB_HOME/bin"
  cp "$W/gl/gitleaks" "$G/gitleaks.tmp" && chmod 0755 "$G/gitleaks.tmp" && mv -f "$G/gitleaks.tmp" "$G/gitleaks"
  ln -sfn ../tools/gitleaks/8.30.1/gitleaks "$BOB_HOME/bin/gitleaks"
  echo "bob-prompt: gitleaks: ok"
fi
```

```sh bob-step=gitleaks platform=darwin-x64
set -eu
fail() { printf 'bob-prompt: %s\n' "$*" >&2; exit 4; }
case "${XDG_DATA_HOME:-}" in /*) D="$XDG_DATA_HOME" ;; *) D="$HOME/.local/share" ;; esac
BOB_HOME="${BOB_HOME:-$D/bob-quality}"
case "$BOB_HOME" in /*) ;; *) fail "launcher: BOB_HOME=$BOB_HOME must be absolute" ;; esac
W="${TMPDIR:-/tmp}/bob-install-$(id -u)"
A=gitleaks_8.30.1_darwin_x64.tar.gz
S=dfe101a4db2255fc85120ac7f3d25e4342c3c20cf749f2c20a18081af1952709
G="$BOB_HOME/tools/gitleaks/8.30.1"
GB=${BOB_GITLEAKS_BASE_URL:-https://github.com/gitleaks/gitleaks/releases/download/v8.30.1}; GB=${GB%/}
case "$GB" in https://*|http://127.0.0.1|http://127.0.0.1[:/]*|http://localhost|http://localhost[:/]*) ;; *) fail "gitleaks: BOB_GITLEAKS_BASE_URL=$GB is not allowed" ;; esac
if [ -x "$BOB_HOME/bin/gitleaks" ] && "$BOB_HOME/bin/gitleaks" --version 2>/dev/null | grep -qF 8.30.1; then
  echo "bob-prompt: gitleaks: ok (reused)"
else
  curl -fsSL --connect-timeout 15 --max-time 300 --retry 2 -o "$W/$A" "$GB/$A" || fail "gitleaks: download of $GB/$A failed; check the network and try again"
  [ "$(shasum -a 256 "$W/$A" | awk '{ print $1 }')" = "$S" ] || fail "gitleaks: the sha256 of $A does not match; nothing was installed"
  rm -rf "$W/gl" && mkdir "$W/gl"
  tar -xzf "$W/$A" -C "$W/gl" gitleaks 2>/dev/null || fail "gitleaks: $A does not have the expected gitleaks binary; nothing was installed"
  [ -f "$W/gl/gitleaks" ] && [ ! -L "$W/gl/gitleaks" ] || fail "gitleaks: $A does not have the expected gitleaks binary; nothing was installed"
  mkdir -p "$G" "$BOB_HOME/bin"
  cp "$W/gl/gitleaks" "$G/gitleaks.tmp" && chmod 0755 "$G/gitleaks.tmp" && mv -f "$G/gitleaks.tmp" "$G/gitleaks"
  ln -sfn ../tools/gitleaks/8.30.1/gitleaks "$BOB_HOME/bin/gitleaks"
  echo "bob-prompt: gitleaks: ok"
fi
```

```sh bob-step=gitleaks platform=darwin-arm64
set -eu
fail() { printf 'bob-prompt: %s\n' "$*" >&2; exit 4; }
case "${XDG_DATA_HOME:-}" in /*) D="$XDG_DATA_HOME" ;; *) D="$HOME/.local/share" ;; esac
BOB_HOME="${BOB_HOME:-$D/bob-quality}"
case "$BOB_HOME" in /*) ;; *) fail "launcher: BOB_HOME=$BOB_HOME must be absolute" ;; esac
W="${TMPDIR:-/tmp}/bob-install-$(id -u)"
A=gitleaks_8.30.1_darwin_arm64.tar.gz
S=b40ab0ae55c505963e365f271a8d3846efbc170aa17f2607f13df610a9aeb6a5
G="$BOB_HOME/tools/gitleaks/8.30.1"
GB=${BOB_GITLEAKS_BASE_URL:-https://github.com/gitleaks/gitleaks/releases/download/v8.30.1}; GB=${GB%/}
case "$GB" in https://*|http://127.0.0.1|http://127.0.0.1[:/]*|http://localhost|http://localhost[:/]*) ;; *) fail "gitleaks: BOB_GITLEAKS_BASE_URL=$GB is not allowed" ;; esac
if [ -x "$BOB_HOME/bin/gitleaks" ] && "$BOB_HOME/bin/gitleaks" --version 2>/dev/null | grep -qF 8.30.1; then
  echo "bob-prompt: gitleaks: ok (reused)"
else
  curl -fsSL --connect-timeout 15 --max-time 300 --retry 2 -o "$W/$A" "$GB/$A" || fail "gitleaks: download of $GB/$A failed; check the network and try again"
  [ "$(shasum -a 256 "$W/$A" | awk '{ print $1 }')" = "$S" ] || fail "gitleaks: the sha256 of $A does not match; nothing was installed"
  rm -rf "$W/gl" && mkdir "$W/gl"
  tar -xzf "$W/$A" -C "$W/gl" gitleaks 2>/dev/null || fail "gitleaks: $A does not have the expected gitleaks binary; nothing was installed"
  [ -f "$W/gl/gitleaks" ] && [ ! -L "$W/gl/gitleaks" ] || fail "gitleaks: $A does not have the expected gitleaks binary; nothing was installed"
  mkdir -p "$G" "$BOB_HOME/bin"
  cp "$W/gl/gitleaks" "$G/gitleaks.tmp" && chmod 0755 "$G/gitleaks.tmp" && mv -f "$G/gitleaks.tmp" "$G/gitleaks"
  ln -sfn ../tools/gitleaks/8.30.1/gitleaks "$BOB_HOME/bin/gitleaks"
  echo "bob-prompt: gitleaks: ok"
fi
```

## 12. perfil

```sh bob-step=perfil platform=all
set -eu
fail() { printf 'bob-prompt: %s\n' "$*" >&2; exit 4; }
case "${XDG_DATA_HOME:-}" in /*) D="$XDG_DATA_HOME" ;; *) D="$HOME/.local/share" ;; esac
BOB_HOME="${BOB_HOME:-$D/bob-quality}"
case "$BOB_HOME" in /*) ;; *) fail "launcher: BOB_HOME=$BOB_HOME must be absolute" ;; esac
W="${TMPDIR:-/tmp}/bob-install-$(id -u)"
LINE='export PATH="$HOME/.local/bin:$PATH" # managed-by: bob-quality'
case ":$PATH:" in
  *":$HOME/.local/bin:"*) R=already-on-path ;;
  *)
    S=${SHELL:-}
    case "${S##*/}" in
      zsh) F="${ZDOTDIR:-$HOME}/.zshrc" ;;
      bash) F="$HOME/.bashrc" ;;
      *) F="$HOME/.profile" ;;
    esac
    if [ -f "$F" ] && grep -qF '# managed-by: bob-quality' "$F"; then
      R="already-marked:$F"
    elif { [ -e "$F" ] || { : > "$F" && chmod 0644 "$F"; }; } 2>/dev/null && { if [ -s "$F" ] && [ -n "$(tail -c 1 "$F")" ]; then printf '\n'; fi; printf '%s\n' "$LINE"; } >> "$F" 2>/dev/null; then
      R=$F
    else
      R="failed:$F"
      echo "bob-prompt: perfil: warning: could not write $F. To use the bob command, add to your profile: export PATH=\"\$HOME/.local/bin:\$PATH\""
    fi ;;
esac
printf '%s\n' "$R" > "$W/profile"
echo "bob-prompt: perfil: $R"
```

## 13. setup

```sh bob-step=setup platform=all
set -eu
fail() { printf 'bob-prompt: %s\n' "$*" >&2; exit 4; }
case "${XDG_DATA_HOME:-}" in /*) D="$XDG_DATA_HOME" ;; *) D="$HOME/.local/share" ;; esac
BOB_HOME="${BOB_HOME:-$D/bob-quality}"
case "$BOB_HOME" in /*) ;; *) fail "launcher: BOB_HOME=$BOB_HOME must be absolute" ;; esac
W="${TMPDIR:-/tmp}/bob-install-$(id -u)"
[ "$(pwd -P)" = "$(cat "$W/project")" ] || fail "setup: run this block in the project root $(cat "$W/project")"
BOB_INSTALL_PROFILE="$(cat "$W/profile")" "$BOB_HOME/bin/bob" setup --lang "${BOB_LANG:-en}" || fail "setup: bob setup exited $?; see the output above"
```

## 14. verificação

```sh bob-step=verificação platform=all
set -eu
fail() { printf 'bob-prompt: %s\n' "$*" >&2; exit 4; }
case "${XDG_DATA_HOME:-}" in /*) D="$XDG_DATA_HOME" ;; *) D="$HOME/.local/share" ;; esac
BOB_HOME="${BOB_HOME:-$D/bob-quality}"
case "$BOB_HOME" in /*) ;; *) fail "launcher: BOB_HOME=$BOB_HOME must be absolute" ;; esac
W="${TMPDIR:-/tmp}/bob-install-$(id -u)"
V=$(cat "$W/version"); X=${V#v}
if "$BOB_HOME/bin/bob" doctor; then d=0; else d=$?; fi
BOB_LANG=en "$BOB_HOME/bin/bob" --version > "$W/version.out" || fail "verificação: bob --version failed"
cat "$W/version.out"
[ "$d" -eq 0 ] || fail "verificação: bob doctor exited $d, expected 0"
[ "$(sed -n 1p "$W/version.out")" = "bob $X" ] || fail "verificação: bob --version does not show bob $X"
[ "$(sed -n 2p "$W/version.out")" = "project skills: $X (.agents/skills)" ] || fail "verificação: project skills are not at $X"
rm -rf "$W"
echo "bob-prompt: verificação: ok (bob $X, bob doctor 0)"
```

> Tests/release-check only: BOB_VERSION=vX.Y.Z pins the tag (e.g. a pre-release in the release-check). Otherwise, do not set it; the prompt installs the latest published release.
