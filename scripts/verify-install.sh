#!/bin/sh
# Harness do comando de verificação (CT15): passos 1, 2, 3, 4, 5, 6, 7, 8, 9a, 9b e 12.
set -u
STEP_IDS='1 2 3 4 5 6 7 8 9a 9b 12'
GITLEAKS_VERSION='8.30.1'
GITLEAKS_SHA_LINUX_X64='551f6fc83ea457d62a0d98237cbad105af8d557003051f41f3e7ca7b3f2470eb'
GITLEAKS_SHA_LINUX_ARM64='e4a487ee7ccd7d3a7f7ec08657610aa3606637dab924210b3aee62570fb4b080'
GITLEAKS_SHA_DARWIN_X64='dfe101a4db2255fc85120ac7f3d25e4342c3c20cf749f2c20a18081af1952709'
GITLEAKS_SHA_DARWIN_ARM64='b40ab0ae55c505963e365f271a8d3846efbc170aa17f2607f13df610a9aeb6a5'

T=
SERVER_PID=
STEP2_DONE=0
remote=0
BASE=
X=
TAG=
WHL=
NODE_DIR=
PY_DIR=
S2_HOME=
S2_PROJ=
selected=
GL_ASSET=
GL_URL=

die_usage() {
  printf 'verify-install: uso: %s\n' "$1" >&2
  exit 1
}

die_preparo() {
  printf 'verify-install: preparo: %s\n' "$1" >&2
  exit 1
}

die_passo() {
  printf 'verify-install: passo %s: %s\n' "$1" "$2" >&2
  exit 1
}

ok() {
  printf 'verify-install: passo %s: ok\n' "$1"
}

cleanup() {
  _status=$?
  if [ -n "$SERVER_PID" ]; then
    kill "$SERVER_PID" 2>/dev/null || true
    wait "$SERVER_PID" 2>/dev/null || true
  fi
  if [ "$_status" -eq 0 ]; then
    if [ -n "$T" ]; then
      rm -rf "$T"
    fi
  elif [ -n "$T" ]; then
    printf 'verify-install: temporário guardado em %s\n' "$T" >&2
  fi
  exit "$_status"
}

_select() {
  for _have in $selected; do
    if [ "$_have" = "$1" ]; then
      return 0
    fi
  done
  selected="$selected $1"
}

_expand_id() {
  _id=$1
  if [ "$_id" = 9 ]; then
    for _step in $STEP_IDS; do
      case "$_step" in
        9*) _select "$_step" ;;
      esac
    done
    return 0
  fi
  _known=0
  for _step in $STEP_IDS; do
    if [ "$_step" = "$_id" ]; then
      _known=1
    fi
  done
  if [ "$_known" -eq 0 ]; then
    die_usage "passo desconhecido $_id. Passos: $STEP_IDS."
  fi
  _select "$_id"
}

parse_args() {
  only_raw=
  saw_only=0
  while [ "$#" -gt 0 ]; do
    case "$1" in
      --help)
        printf '%s\n' 'uso: sh scripts/verify-install.sh [--only <id>[,<id>...]]'
        printf '%s\n' "passos: $STEP_IDS"
        printf '%s\n' 'VERIFY_REMOTE=1 usa o GitHub em vez do espelho local.'
        exit 0
        ;;
      --only)
        if [ "$#" -lt 2 ]; then
          die_usage '--only. Rode com --help.'
        fi
        only_raw=$2
        saw_only=1
        shift 2
        ;;
      *)
        die_usage "$1. Rode com --help."
        ;;
    esac
  done
  if [ "$saw_only" -eq 0 ]; then
    selected=$STEP_IDS
    return 0
  fi
  selected=
  _old_ifs=$IFS
  IFS=,
  for _id in $only_raw; do
    IFS=$_old_ifs
    _expand_id "$_id"
  done
  IFS=$_old_ifs
}

file_sha() {
  if command -v sha256sum >/dev/null 2>&1; then
    sha256sum "$1" | awk '{ print $1 }'
    return 0
  fi
  shasum -a 256 "$1" | awk '{ print $1 }'
}

digest() {
  _py=$(cat <<'PY'
import hashlib
import os
import sys

root = os.path.abspath(sys.argv[1])

def relative(path):
    return os.path.relpath(path, root).replace(os.sep, "/")

def keep(path_rel):
    parts = path_rel.split("/")
    if parts[0] != ".git":
        return True
    if path_rel == ".git":
        return True
    return len(parts) > 1 and parts[1] == "hooks"

def describe(path):
    info = os.lstat(path)
    mode = format(info.st_mode & 0o777, "o")
    if os.path.islink(path):
        kind = "link"
        extra = os.readlink(path)
    elif os.path.isdir(path):
        kind = "dir"
        extra = "-"
    else:
        kind = "file"
        digest = hashlib.sha256()
        handle = open(path, "rb")
        try:
            chunk = handle.read(65536)
            while chunk:
                digest.update(chunk)
                chunk = handle.read(65536)
        finally:
            handle.close()
        extra = digest.hexdigest()
    return relative(path) + "\t" + kind + "\t" + extra + "\t" + mode

rows = []
for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
    current = relative(dirpath)
    if current != "." and not keep(current):
        dirnames[:] = []
        continue
    if current == ".git":
        dirnames[:] = [name for name in dirnames if name == "hooks"]
    linked = []
    for name in dirnames:
        path = os.path.join(dirpath, name)
        if os.path.islink(path):
            linked.append(name)
    for name in linked:
        dirnames.remove(name)
        path = os.path.join(dirpath, name)
        rel = relative(path)
        if keep(rel):
            rows.append(describe(path))
    if current != "." and keep(current):
        rows.append(describe(dirpath))
    for name in filenames:
        path = os.path.join(dirpath, name)
        rel = relative(path)
        if keep(rel):
            rows.append(describe(path))
rows.sort()
sys.stdout.write("\n".join(rows))
PY
)
  "$PY_DIR/python3" -c "$_py" "$1"
}

first_diff() {
  "$PY_DIR/python3" -c '
import sys
before = open(sys.argv[1], encoding="utf-8").read().splitlines()
after = open(sys.argv[2], encoding="utf-8").read().splitlines()
width = len(before)
if len(after) > width:
    width = len(after)
index = 0
while index < width:
    left = ""
    right = ""
    if index < len(before):
        left = before[index]
    if index < len(after):
        right = after[index]
    if left != right:
        if right:
            sys.stdout.write(right)
        else:
            sys.stdout.write(left)
        break
    index = index + 1
' "$1" "$2"
}

last_nonempty() {
  "$PY_DIR/python3" -c '
import sys
lines = open(sys.argv[1], encoding="utf-8", errors="replace").read().splitlines()
index = len(lines) - 1
while index >= 0:
    if lines[index] != "":
        sys.stdout.write(lines[index])
        break
    index = index - 1
' "$1"
}

line_count() {
  "$PY_DIR/python3" -c '
import sys
text = open(sys.argv[1], encoding="utf-8", errors="replace").read()
print(len(text.splitlines()))
' "$1"
}

mirror_new() {
  "$PY_DIR/python3" -c '
import re
import sys
start = int(sys.argv[1])
lines = open(sys.argv[2], encoding="utf-8", errors="replace").read().splitlines()
rows = []
for line in lines[start:]:
    if line == "":
        continue
    match = re.search(r"\"([A-Z]+) (\S+) HTTP/[^\"]*\" (\d+)", line)
    if match is None:
        rows.append(line)
    else:
        rows.append(match.group(1) + " " + match.group(2) + " " + match.group(3))
sys.stdout.write("\n".join(rows))
' "$1" "$2"
}

file_mtime() {
  "$PY_DIR/python3" -c '
import os
import sys
print(os.stat(sys.argv[1]).st_mtime_ns)
' "$1"
}

read_meta() {
  "$PY_DIR/python3" -c '
import pathlib
text = pathlib.Path("pyproject.toml").read_text(encoding="utf-8")
version = ""
pin = ""
section = ""
for line in text.splitlines():
    if line.startswith("[") and line.endswith("]"):
        section = line
        continue
    if section == "[project]" and version == "" and line.startswith("version") and "=" in line:
        raw = line.split("=", 1)[1].strip()
        if len(raw) >= 2 and raw[0] == "\"" and raw[-1] == "\"":
            version = raw[1:-1]
    stripped = line.strip().strip(",")
    inner = stripped
    if len(stripped) >= 2 and stripped[0] == "\"" and stripped[-1] == "\"":
        inner = stripped[1:-1]
    if inner.startswith("build==") and pin == "":
        pin = inner
print(version)
print(pin)
'
}

bob_vitest() {
  "$PY_DIR/python3" -c '
import json
print(json.load(open("package.json", encoding="utf-8"))["dependencies"]["vitest"])
'
}

show_file() {
  "$PY_DIR/python3" -c '
import pathlib
import sys
text = pathlib.Path(sys.argv[1]).read_text(encoding="utf-8")
sys.stdout.write(text.replace("\n", "\\n"))
' "$1"
}

new_project() {
  _proj=$1
  _file=${2:-src/app.py}
  mkdir -p "$_proj/$(dirname "$_file")" || return 1
  (
    cd "$_proj" || exit 1
    git init -q || exit 1
    git config user.email verify@example.invalid || exit 1
    git config user.name verify || exit 1
    printf '%s\n' 'print("app")' > "$_file" || exit 1
    git add -A || exit 1
    git commit -qm init || exit 1
  )
}

release_pair() {
  if [ "$remote" -eq 1 ]; then
    REL_URL=https://github.com/fazedordecodigo/bob/releases
    REL_ENV=
    GL_URL=
  else
    REL_URL=$BASE
    REL_ENV=$BASE
    GL_URL=$BASE/gitleaks
  fi
}

run_oneliner() {
  _step=$1
  _home=$2
  _tmp=$3
  _proj=$4
  _releases=$5
  _url=$6
  _path=$7
  _out=$8
  _err=$9
  _bob=$(PATH="$_path" command -v bob 2>/dev/null) || _bob=
  if [ -n "$_bob" ]; then
    die_passo "$_step" "bob já está no PATH ($_bob); a máquina não está limpa."
  fi
  _gl=$(PATH="$_path" command -v gitleaks 2>/dev/null) || _gl=
  if [ -n "$_gl" ]; then
    die_passo "$_step" "gitleaks já está no PATH ($_gl); a máquina não está limpa."
  fi
  set -- env -i "HOME=$_home" "TMPDIR=$_tmp" LANG=C.UTF-8 "PATH=$_path"
  if [ -n "$_releases" ]; then
    set -- "$@" "BOB_RELEASES_URL=$_releases"
  fi
  if [ -n "$GL_URL" ]; then
    set -- "$@" "BOB_GITLEAKS_BASE_URL=$GL_URL"
  fi
  for _name in PIP_INDEX_URL PIP_EXTRA_INDEX_URL PIP_TRUSTED_HOST PIP_CERT \
    npm_config_registry npm_config_cache \
    http_proxy https_proxy HTTP_PROXY HTTPS_PROXY \
    no_proxy NO_PROXY SSL_CERT_FILE SSL_CERT_DIR
  do
    eval "_isset=\${$_name+x}"
    if [ "$_isset" = x ]; then
      eval "_value=\${$_name}"
      set -- "$@" "$_name=$_value"
    fi
  done
  set -- "$@" sh -c 'curl -fsSL "$1/latest/download/install.sh" | sh' _ "$_url"
  (
    cd "$_proj" || exit 99
    "$@"
  ) >"$_out" 2>"$_err"
  return $?
}

tool_path() {
  printf '%s' "$T/fake-sudo:$NODE_DIR:$PY_DIR:/usr/bin:/bin"
}

node_floor() {
  sed -n "s/^NODE_FLOOR='\([^']*\)'/\1/p" scripts/install.sh
}

node_below() {
  sed -n "s/^NODE_BELOW='\([^']*\)'/\1/p" scripts/install.sh
}

cites_node() {
  _floor=$1
  _below=$2
  _file=$3
  _range=">=$_floor <$_below"
  while IFS= read -r _line || [ -n "$_line" ]; do
    case "$_line" in
      "install: node:"*)
        case "$_line" in
          *v20.0.0*)
            case "$_line" in
              *"$_range"*) return 0 ;;
            esac
            ;;
        esac
        ;;
    esac
  done < "$_file"
  return 1
}

cites_integrity() {
  while IFS= read -r _line || [ -n "$_line" ]; do
    case "$_line" in
      "install: integridade:"*) return 0 ;;
    esac
  done < "$1"
  return 1
}

prepare_runtime() {
  _node=$(command -v node 2>/dev/null) || _node=
  if [ -z "$_node" ]; then
    die_preparo "node não encontrado no PATH"
  fi
  NODE_DIR=$(dirname "$_node")
  if [ ! -x "$NODE_DIR/node" ] || [ ! -x "$NODE_DIR/npm" ]; then
    die_preparo "node não encontrado no PATH"
  fi
  _prefix=$(python3 -c 'import sys; print(sys.base_prefix)') || _prefix=
  PY_DIR="$_prefix/bin"
  if [ -z "$_prefix" ] || [ ! -x "$PY_DIR/python3" ]; then
    die_preparo "python3 base sem bin/python3 em ${_prefix:-?}"
  fi
}

build_wheel() {
  : > "$T/build.log"
  _meta=$(read_meta) || die_preparo "build do wheel falhou (veja $T/build.log)"
  X=$(printf '%s\n' "$_meta" | sed -n '1p')
  _pin=$(printf '%s\n' "$_meta" | sed -n '2p')
  if [ -z "$X" ] || [ -z "$_pin" ]; then
    printf '%s\n' "versão ou pin vazio" >> "$T/build.log"
    die_preparo "build do wheel falhou (veja $T/build.log)"
  fi
  TAG="v$X"
  WHL="bob_quality-$X-py3-none-any.whl"
  if ! "$PY_DIR/python3" -m venv "$T/build-venv" >>"$T/build.log" 2>&1; then
    die_preparo "build do wheel falhou (veja $T/build.log)"
  fi
  if ! "$T/build-venv/bin/pip" install "$_pin" >>"$T/build.log" 2>&1; then
    die_preparo "build do wheel falhou (veja $T/build.log)"
  fi
  mkdir -p "$T/dist" || die_preparo "build do wheel falhou (veja $T/build.log)"
  if ! "$T/build-venv/bin/python" -m build --wheel --outdir "$T/dist" \
    >>"$T/build.log" 2>&1; then
    die_preparo "build do wheel falhou (veja $T/build.log)"
  fi
  if [ ! -f "$T/dist/$WHL" ]; then
    die_preparo "build do wheel falhou (veja $T/build.log)"
  fi
}

copy_three() {
  _dest=$1
  mkdir -p "$_dest" || return 1
  cp "$T/stage/install.sh" "$_dest/install.sh" || return 1
  cp "$T/stage/$WHL" "$_dest/$WHL" || return 1
  cp "$T/stage/SHA256SUMS" "$_dest/SHA256SUMS" || return 1
}

build_mirror() {
  mkdir -p "$T/stage" || die_preparo "não consegui montar o espelho"
  cp scripts/install.sh "$T/stage/install.sh" || die_preparo "não consegui montar o espelho"
  cp "$T/dist/$WHL" "$T/stage/$WHL" || die_preparo "não consegui montar o espelho"
  (
    cd "$T/stage" || exit 1
    if command -v sha256sum >/dev/null 2>&1; then
      sha256sum install.sh "$WHL" | LC_ALL=C sort -k2
    elif command -v shasum >/dev/null 2>&1; then
      shasum -a 256 install.sh "$WHL" | LC_ALL=C sort -k2
    else
      exit 1
    fi
  ) > "$T/stage/SHA256SUMS" || die_preparo "não consegui montar o espelho"
  if [ ! -s "$T/stage/SHA256SUMS" ]; then
    die_preparo "não consegui montar o espelho"
  fi
  mkdir -p "$T/mirror/api/releases" "$T/mirror/bad/api/releases" \
    || die_preparo "não consegui montar o espelho"
  _latest="{\"tag_name\": \"$TAG\", \"name\": \"$TAG\", \"draft\": false, \"prerelease\": false}"
  printf '%s\n' "$_latest" > "$T/mirror/api/releases/latest" \
    || die_preparo "não consegui montar o espelho"
  cp "$T/mirror/api/releases/latest" "$T/mirror/bad/api/releases/latest" \
    || die_preparo "não consegui montar o espelho"
  copy_three "$T/mirror/download/$TAG" || die_preparo "não consegui montar o espelho"
  copy_three "$T/mirror/latest/download" || die_preparo "não consegui montar o espelho"
  copy_three "$T/mirror/download/v99.0.0-rc.1" \
    || die_preparo "não consegui montar o espelho"
  printf '%s\n' \
    '{"tag_name": "v99.0.0-rc.1", "name": "v99.0.0-rc.1", "draft": false, "prerelease": true}' \
    > "$T/mirror/prerelease.json" || die_preparo "não consegui montar o espelho"
  copy_three "$T/mirror/drafts/v99.0.1" || die_preparo "não consegui montar o espelho"
  mkdir -p "$T/mirror/bad/download/$TAG" "$T/mirror/bad/latest/download" \
    || die_preparo "não consegui montar o espelho"
  cp "$T/stage/install.sh" "$T/mirror/bad/download/$TAG/install.sh" \
    || die_preparo "não consegui montar o espelho"
  cp "$T/stage/SHA256SUMS" "$T/mirror/bad/download/$TAG/SHA256SUMS" \
    || die_preparo "não consegui montar o espelho"
  cp "$T/stage/$WHL" "$T/mirror/bad/download/$TAG/$WHL" \
    || die_preparo "não consegui montar o espelho"
  printf '\n' >> "$T/mirror/bad/download/$TAG/$WHL" \
    || die_preparo "não consegui montar o espelho"
  cp "$T/stage/install.sh" "$T/mirror/bad/latest/download/install.sh" \
    || die_preparo "não consegui montar o espelho"
}

start_server() {
  port=$("$PY_DIR/python3" -c '
import socket
sock = socket.socket()
sock.bind(("127.0.0.1", 0))
print(sock.getsockname()[1])
sock.close()
') || die_preparo "o espelho não respondeu em 10 s"
  PYTHONUNBUFFERED=1 "$PY_DIR/python3" -m http.server --bind 127.0.0.1 "$port" \
    --directory "$T/mirror" >"$T/mirror.log" 2>&1 &
  SERVER_PID=$!
  _ready=0
  _i=0
  while [ "$_i" -lt 10 ]; do
    if curl -fsS "http://127.0.0.1:$port/api/releases/latest" >/dev/null 2>&1; then
      _ready=1
      break
    fi
    _i=$((_i + 1))
    sleep 1
  done
  if [ "$_ready" -ne 1 ]; then
    die_preparo "o espelho não respondeu em 10 s"
  fi
  BASE="http://127.0.0.1:$port"
}

prepare_gitleaks() {
  _os=$(uname -s)
  _mach=$(uname -m)
  case "$_os" in
    Linux) _gos=linux ;;
    Darwin) _gos=darwin ;;
    *) die_preparo "gitleaks: download falhou" ;;
  esac
  case "$_mach" in
    x86_64|amd64) _garch=x64 ;;
    aarch64|arm64) _garch=arm64 ;;
    *) die_preparo "gitleaks: download falhou" ;;
  esac
  case "${_gos}_${_garch}" in
    linux_x64) _want=$GITLEAKS_SHA_LINUX_X64 ;;
    linux_arm64) _want=$GITLEAKS_SHA_LINUX_ARM64 ;;
    darwin_x64) _want=$GITLEAKS_SHA_DARWIN_X64 ;;
    darwin_arm64) _want=$GITLEAKS_SHA_DARWIN_ARM64 ;;
    *) die_preparo "gitleaks: download falhou" ;;
  esac
  _asset="gitleaks_${GITLEAKS_VERSION}_${_gos}_${_garch}.tar.gz"
  _cache_root=${XDG_CACHE_HOME:-$HOME/.cache}
  mkdir -p "$_cache_root/bob-verify-install" || die_preparo "gitleaks: download falhou"
  _cache="$_cache_root/bob-verify-install/$_asset"
  _need=1
  if [ -f "$_cache" ]; then
    _got=$(file_sha "$_cache")
    if [ "$_got" = "$_want" ]; then
      _need=0
    fi
  fi
  if [ "$_need" -eq 1 ]; then
    _partial="$_cache.partial"
    _url="https://github.com/gitleaks/gitleaks/releases/download/v${GITLEAKS_VERSION}/$_asset"
    if ! curl -fsSL --connect-timeout 15 --max-time 300 --retry 2 \
      -o "$_partial" "$_url"; then
      rm -f "$_partial"
      die_preparo "gitleaks: download falhou"
    fi
    _got=$(file_sha "$_partial")
    if [ "$_got" != "$_want" ]; then
      rm -f "$_partial"
      die_preparo "gitleaks: sha256 de $_asset não confere"
    fi
    mv "$_partial" "$_cache" || die_preparo "gitleaks: download falhou"
  fi
  mkdir -p "$T/mirror/gitleaks" "$T/mirror/gitleaks-bad" \
    || die_preparo "não consegui montar o espelho"
  cp "$_cache" "$T/mirror/gitleaks/$_asset" \
    || die_preparo "não consegui montar o espelho"
  cp "$_cache" "$T/mirror/gitleaks-bad/$_asset" \
    || die_preparo "não consegui montar o espelho"
  printf '\n' >> "$T/mirror/gitleaks-bad/$_asset" \
    || die_preparo "não consegui montar o espelho"
  GL_ASSET=$_asset
}

prepare_fakes() {
  mkdir -p "$T/fake-sudo" "$T/fake-node20" || die_preparo "não consegui criar o temporário"
  : > "$T/sudo.log"
  cat > "$T/fake-sudo/sudo" <<EOF
#!/bin/sh
printf '%s\n' "\$*" >> '$T/sudo.log'
exit 1
EOF
  cat > "$T/fake-node20/node" <<'EOF'
#!/bin/sh
printf '%s\n' 'v20.0.0'
EOF
  cat > "$T/fake-node20/npm" <<'EOF'
#!/bin/sh
printf '%s\n' '10.0.0'
EOF
  chmod 0755 "$T/fake-sudo/sudo" "$T/fake-node20/node" "$T/fake-node20/npm"
}

prepare() {
  T=$(mktemp -d "${TMPDIR:-/tmp}/bob-verify.XXXXXX") \
    || die_preparo "não consegui criar o temporário"
  prepare_runtime
  if [ "$remote" -eq 0 ]; then
    build_wheel
    build_mirror
    prepare_gitleaks
    start_server
  fi
  prepare_fakes
}

lock_of() {
  _home=$1
  _found=
  for _path in "$_home/.local/share/bob-quality/versions/$X/venv/lib/python"*/site-packages/bob_quality/node_modules/.package-lock.json; do
    if [ -f "$_path" ]; then
      _found=$_path
      break
    fi
  done
  if [ -z "$_found" ]; then
    _alt="$_home/.cache/bob-quality/node_modules/.package-lock.json"
    if [ -f "$_alt" ]; then
      _found=$_alt
    fi
  fi
  printf '%s' "$_found"
}

step_1() {
  mkdir -p "$T/s1/home" "$T/s1/tmp" "$T/s1/proj" \
    || die_passo 1 "não consegui criar o projeto"
  new_project "$T/s1/proj" || die_passo 1 "não consegui criar o projeto"
  digest "$T/s1/proj" > "$T/s1/before.txt" || die_passo 1 "o projeto mudou:"
  _path="$T/fake-node20:$(tool_path)"
  release_pair
  run_oneliner 1 "$T/s1/home" "$T/s1/tmp" "$T/s1/proj" \
    "$REL_ENV" "$REL_URL" "$_path" "$T/s1/out.log" "$T/s1/err.log"
  _rc=$?
  if [ "$_rc" -eq 0 ]; then
    die_passo 1 "saiu 0 com node 20"
  fi
  _floor=$(node_floor)
  _below=$(node_below)
  if ! cites_node "$_floor" "$_below" "$T/s1/err.log"; then
    die_passo 1 "stderr não cita a faixa do node"
  fi
  digest "$T/s1/proj" > "$T/s1/after.txt" || die_passo 1 "o projeto mudou:"
  if ! cmp -s "$T/s1/before.txt" "$T/s1/after.txt"; then
    die_passo 1 "o projeto mudou: $(first_diff "$T/s1/before.txt" "$T/s1/after.txt")"
  fi
  if [ -e "$T/s1/home/.local/share/bob-quality" ] \
    || [ -L "$T/s1/home/.local/share/bob-quality" ]; then
    die_passo 1 "BOB_HOME foi criado"
  fi
  if [ -s "$T/sudo.log" ]; then
    _line=
    IFS= read -r _line < "$T/sudo.log" || _line=
    die_passo 1 "o sudo foi chamado: $_line"
  fi
  ok 1
}

step_2() {
  mkdir -p "$T/s2/home" "$T/s2/tmp" "$T/s2/proj" \
    || die_passo 2 "não consegui criar o projeto"
  new_project "$T/s2/proj" || die_passo 2 "não consegui criar o projeto"
  S2_HOME=$T/s2/home
  S2_PROJ=$T/s2/proj
  _mark=
  if [ "$remote" -eq 0 ]; then
    _mark=$(line_count "$T/mirror.log")
  fi
  release_pair
  _t0=$(date +%s)
  run_oneliner 2 "$S2_HOME" "$T/s2/tmp" "$S2_PROJ" \
    "$REL_ENV" "$REL_URL" "$(tool_path)" "$T/s2/out.log" "$T/s2/err.log"
  _rc=$?
  _t1=$(date +%s)
  _secs=$((_t1 - _t0))
  if [ "$_rc" -ne 0 ]; then
    die_passo 2 "saiu $_rc; veja $T/s2/out.log"
  fi
  if [ "$_secs" -gt 300 ]; then
    die_passo 2 "levou $_secs s (máx. 300)"
  fi
  _last=$(last_nonempty "$T/s2/out.log")
  if [ "$_last" != "  bob doctor: 0" ]; then
    die_passo 2 "a última linha não é \"  bob doctor: 0\""
  fi
  if grep -F 'git clone' "$T/s2/out.log" "$T/s2/err.log" >/dev/null 2>&1; then
    die_passo 2 "o log contém git clone"
  fi
  if [ "$remote" -eq 0 ]; then
    _got=$(mirror_new "$_mark" "$T/mirror.log")
    _want="GET /latest/download/install.sh 200
GET /api/releases/latest 200
GET /download/$TAG/$WHL 200
GET /download/$TAG/SHA256SUMS 200
GET /gitleaks/$GL_ASSET 200"
    if [ "$_got" != "$_want" ]; then
      _flat=$(printf '%s' "$_got" | tr '\n' ',' | sed 's/,$//')
      die_passo 2 "pedidos ao espelho: $_flat"
    fi
  fi
  check_gitleaks_install 2 "$S2_HOME"
  printf 'verify-install: passo 2: tempo %s s\n' "$_secs"
  ok 2
}

check_gitleaks_install() {
  BH="$2/.local/share/bob-quality"
  _link=$(readlink "$BH/bin/gitleaks") || _link=
  if [ "$_link" != "../tools/gitleaks/$GITLEAKS_VERSION/gitleaks" ]; then
    die_passo "$1" "BOB_HOME/bin/gitleaks não é o link esperado"
  fi
  _ver=$("$BH/bin/gitleaks" version 2>/dev/null) || true
  if [ "$_ver" != "$GITLEAKS_VERSION" ]; then
    die_passo "$1" "BOB_HOME/bin/gitleaks version = $_ver"
  fi
  _mode=$("$PY_DIR/python3" -c 'import os, sys; print(format(os.stat(sys.argv[1]).st_mode & 0o777, "o"))' \
    "$BH/tools/gitleaks/$GITLEAKS_VERSION/gitleaks") || _mode=
  if [ "$_mode" != 755 ]; then
    die_passo "$1" "modo do gitleaks = $_mode"
  fi
}

ensure_2() {
  if [ "$STEP2_DONE" -eq 0 ]; then
    step_2
    STEP2_DONE=1
  fi
}

step_3() {
  if [ -s "$T/sudo.log" ]; then
    _line=
    IFS= read -r _line < "$T/sudo.log" || _line=
    die_passo 3 "o sudo foi chamado: $_line"
  fi
  if [ ! -f "$T/sudo.log" ]; then
    die_passo 3 "o sudo foi chamado:"
  fi
  ok 3
}

step_4() {
  _proj=$S2_PROJ
  printf '%s\n' "$X" > "$T/version-expect"
  for _skill in bob-check harden review-report; do
    _dir="$_proj/.agents/skills/$_skill"
    for _file in SKILL.md .bob-version LICENSE; do
      if [ ! -f "$_dir/$_file" ]; then
        die_passo 4 "falta .agents/skills/$_skill/$_file"
      fi
    done
    if ! cmp -s "$T/version-expect" "$_dir/.bob-version"; then
      die_passo 4 ".bob-version de $_skill = $(show_file "$_dir/.bob-version")"
    fi
  done
  for _base in $(ls -A "$_proj/.agents/skills"); do
    case "$_base" in
      bob-check|harden|review-report) ;;
      *) die_passo 4 "$_base existe" ;;
    esac
  done
  _link=$(find "$_proj/.agents" -type l | sed -n '1p')
  if [ -n "$_link" ]; then
    die_passo 4 "$_link existe"
  fi
  for _banned in .claude .github .cursor .devin; do
    if [ -e "$_proj/$_banned" ] || [ -L "$_proj/$_banned" ]; then
      die_passo 4 "$_banned existe"
    fi
  done
  ok 4
}

expected_bob_yaml() {
  printf '%s\n' \
    'base: origin/main' \
    'language: en' \
    'paths:' \
    "  include: $1" \
    '  exclude: [tests, node_modules, dist]' \
    'crap:' \
    '  max_per_function: 10' \
    '  scope: changed' \
    'duplication:' \
    '  min_tokens: 50' \
    '  new_clones: warn' \
    '  max_new_clones: 0' \
    '  min_similarity: 0' \
    '  min_lines: 0' \
    'coverage:' \
    '  min_percent: 80' \
    'dependencies:' \
    '  python: .importlinter' \
    '  typescript: .dependency-cruiser.cjs'
}

step_5() {
  _t0=
  for _case in src app sem-codigo; do
    _file=src/app.py
    _include='[src]'
    case "$_case" in
      app)
        _file=app/main.py
        _include='[app]'
        ;;
      sem-codigo)
        _file=README.md
        _include='["."]'
        ;;
    esac
    mkdir -p "$T/s5/$_case/proj" "$T/s5/$_case/tmp" \
      && new_project "$T/s5/$_case/proj" "$_file" \
      || die_passo 5 "não consegui criar o projeto $_case"
    release_pair
    if [ -z "$_t0" ]; then
      _t0=$(date +%s)
    fi
    run_oneliner 5 "$S2_HOME" "$T/s5/$_case/tmp" "$T/s5/$_case/proj" \
      "$REL_ENV" "$REL_URL" "$(tool_path)" \
      "$T/s5/$_case/out.log" "$T/s5/$_case/err.log"
    _rc=$?
    if [ "$_rc" -ne 0 ]; then
      die_passo 5 "$_case: saiu $_rc; veja $T/s5/$_case/out.log"
    fi
    _last=$(last_nonempty "$T/s5/$_case/out.log")
    if [ "$_last" != "  bob doctor: 0" ]; then
      die_passo 5 "$_case: a última linha não é \"  bob doctor: 0\""
    fi
    if [ ! -f "$T/s5/$_case/proj/bob.yaml" ]; then
      die_passo 5 "$_case: falta o bob.yaml"
    fi
    expected_bob_yaml "$_include" > "$T/s5/$_case/expected.yaml"
    if ! cmp -s "$T/s5/$_case/expected.yaml" "$T/s5/$_case/proj/bob.yaml"; then
      _diff=$(first_diff "$T/s5/$_case/expected.yaml" \
        "$T/s5/$_case/proj/bob.yaml")
      die_passo 5 "$_case: bob.yaml difere: $_diff"
    fi
    _warn=0
    if grep -Fx \
      'bob setup: bob.yaml: warning: no code folder found; paths.include: ["."].' \
      "$T/s5/$_case/out.log" >/dev/null 2>&1; then
      _warn=1
    fi
    if [ "$_case" = sem-codigo ]; then
      if [ "$_warn" -eq 0 ]; then
        die_passo 5 "$_case: falta o aviso de pasta sem código"
      fi
    elif [ "$_warn" -eq 1 ]; then
      die_passo 5 "$_case: aviso de pasta sem código fora do lugar"
    fi
    (
      cd "$T/s5/$_case/proj" || exit 1
      env -i "HOME=$S2_HOME" "TMPDIR=$T/s5/$_case/tmp" LANG=C.UTF-8 \
        "PATH=$(tool_path)" \
        "$S2_HOME/.local/share/bob-quality/bin/bob" \
        check --base HEAD --gates crap,dry,deps
    ) >"$T/s5/$_case/check.log" 2>&1
    _rc=$?
    if [ "$_rc" -eq 4 ]; then
      die_passo 5 "$_case: bob check saiu 4; veja $T/s5/$_case/check.log"
    fi
  done
  _t1=$(date +%s)
  _secs=$((_t1 - _t0))
  printf 'verify-install: passo 5: tempo %s s\n' "$_secs"
  ok 5
}

expected_hook() {
  printf '%s\n' \
    '#!/bin/sh' \
    '# managed-by: bob-quality' \
    'set -e' \
    'unset PYTEST_ADDOPTS' \
    'unset PYTEST_PLUGINS' \
    "BOB=\"$1\"" \
    '[ -x "$BOB" ] || BOB=bob' \
    'exec "$BOB" check --gates crap,dry,deps </dev/null'
}

step_6() {
  mkdir -p "$T/s6/tmp" "$T/s6/proj" \
    && new_project "$T/s6/proj" \
    && git init -q --bare "$T/s6/remote.git" \
    && (
      cd "$T/s6/proj" || exit 1
      git remote add origin "$T/s6/remote.git" || exit 1
      git push -q origin HEAD:main || exit 1
    ) \
    || die_passo 6 "não consegui criar o projeto"
  release_pair
  run_oneliner 6 "$S2_HOME" "$T/s6/tmp" "$T/s6/proj" \
    "$REL_ENV" "$REL_URL" "$(tool_path)" "$T/s6/out.log" "$T/s6/err.log"
  _rc=$?
  if [ "$_rc" -ne 0 ]; then
    die_passo 6 "saiu $_rc; veja $T/s6/out.log"
  fi
  _last=$(last_nonempty "$T/s6/out.log")
  if [ "$_last" != "  bob doctor: 0" ]; then
    die_passo 6 "a última linha não é \"  bob doctor: 0\""
  fi
  _hook=$T/s6/proj/.git/hooks/pre-push
  if [ ! -f "$_hook" ]; then
    die_passo 6 "falta o hook"
  fi
  expected_hook "$S2_HOME/.local/share/bob-quality/bin/bob" \
    > "$T/s6/expected.hook"
  if ! cmp -s "$T/s6/expected.hook" "$_hook"; then
    _diff=$(first_diff "$T/s6/expected.hook" "$_hook")
    die_passo 6 "o hook difere: $_diff"
  fi
  _mode=$(ls -l "$_hook" | cut -c1-10)
  if [ "$_mode" != "-rwxr-xr-x" ]; then
    die_passo 6 "modo do hook: $_mode"
  fi
  (
    cd "$T/s6/proj" || exit 1
    printf '%s\n' 'def feature():' '    return 1' > src/feature.py || exit 1
    git add -A || exit 1
    git commit -qm feature || exit 1
  ) || die_passo 6 "não consegui criar o commit"
  _t0=$(date +%s)
  (
    cd "$T/s6/proj" || exit 1
    env -i "HOME=$S2_HOME" PATH=/usr/bin:/bin git push origin HEAD:main
  ) >"$T/s6/push.log" 2>&1
  _rc=$?
  _t1=$(date +%s)
  if [ "$_rc" -ne 0 ]; then
    die_passo 6 "o push saiu $_rc; veja $T/s6/push.log"
  fi
  _remote=$(git -C "$T/s6/remote.git" rev-parse main) || _remote=
  _head=$(git -C "$T/s6/proj" rev-parse HEAD) || _head=
  if [ "$_remote" != "$_head" ]; then
    die_passo 6 "o remoto não recebeu o commit"
  fi
  _rep=$T/s6/proj/.bob/report.md
  if [ ! -f "$_rep" ]; then
    die_passo 6 "o hook não rodou o bob check (falta .bob/report.md)"
  fi
  _rep_line=
  IFS= read -r _rep_line < "$_rep" || _rep_line=
  if [ "$_rep_line" != "# bob report" ]; then
    die_passo 6 "relatório inesperado em .bob/report.md"
  fi
  if ! grep -F '`crap`:' "$_rep" >/dev/null 2>&1; then
    die_passo 6 "o relatório não tem o gate crap"
  fi
  if ! grep -F '`dry`:' "$_rep" >/dev/null 2>&1; then
    die_passo 6 "o relatório não tem o gate dry"
  fi
  if ! grep -F '`deps`:' "$_rep" >/dev/null 2>&1; then
    die_passo 6 "o relatório não tem o gate deps"
  fi
  printf 'verify-install: passo 6: tempo %s s\n' "$((_t1 - _t0))"
  ok 6
}

step_7() {
  mkdir -p "$T/s7/tmp" || die_passo 7 "não consegui criar o projeto"
  digest "$S2_PROJ" > "$T/s7/before.txt" || die_passo 7 "a 2ª execução mudou o projeto:"
  _lock=$(lock_of "$S2_HOME")
  _before_m=
  if [ -n "$_lock" ]; then
    _before_m=$(file_mtime "$_lock")
  fi
  _gl_bin=$S2_HOME/.local/share/bob-quality/tools/gitleaks/$GITLEAKS_VERSION/gitleaks
  if [ ! -f "$_gl_bin" ]; then
    die_passo 7 "o gitleaks não está instalado"
  fi
  _gl_before=$(file_mtime "$_gl_bin")
  _hook=$S2_PROJ/.git/hooks/pre-push
  if [ ! -f "$_hook" ]; then
    die_passo 7 "falta o hook"
  fi
  _hook_before=$(file_mtime "$_hook")
  if [ "$remote" -eq 0 ]; then
    _gl_mark=$(line_count "$T/mirror.log")
  fi
  release_pair
  _t0=$(date +%s)
  run_oneliner 7 "$S2_HOME" "$T/s7/tmp" "$S2_PROJ" \
    "$REL_ENV" "$REL_URL" "$(tool_path)" "$T/s7/out.log" "$T/s7/err.log"
  _rc=$?
  _t1=$(date +%s)
  _secs=$((_t1 - _t0))
  if [ "$_rc" -ne 0 ]; then
    die_passo 7 "saiu $_rc; veja $T/s7/out.log"
  fi
  digest "$S2_PROJ" > "$T/s7/after.txt" || die_passo 7 "a 2ª execução mudou o projeto:"
  if ! cmp -s "$T/s7/before.txt" "$T/s7/after.txt"; then
    _diff=$(first_diff "$T/s7/before.txt" "$T/s7/after.txt")
    die_passo 7 "a 2ª execução mudou o projeto: $_diff"
  fi
  if [ "$(file_mtime "$_hook")" != "$_hook_before" ]; then
    die_passo 7 "o hook foi regravado"
  fi
  if ! grep -Fx '  preserved: bob.yaml (already exists; not changed)' \
    "$T/s7/out.log" >/dev/null 2>&1; then
    die_passo 7 "o resumo não lista bob.yaml"
  fi
  _flat=$(
    if [ -d "$S2_HOME/.local/share/bob-quality/versions" ]; then
      ls -A "$S2_HOME/.local/share/bob-quality/versions" | tr '\n' ' ' | sed 's/ $//'
    fi
  )
  if [ "$_flat" != "$X" ]; then
    die_passo 7 "versões: $_flat"
  fi
  if [ "$_secs" -gt 60 ]; then
    die_passo 7 "levou $_secs s (máx. 60)"
  fi
  _lock2=$(lock_of "$S2_HOME")
  if [ -z "$_before_m" ] || [ "$_lock2" != "$_lock" ]; then
    die_passo 7 "npm ci rodou de novo"
  fi
  _after_m=$(file_mtime "$_lock2")
  if [ "$_before_m" != "$_after_m" ]; then
    die_passo 7 "npm ci rodou de novo"
  fi
  _gl_after=$(file_mtime "$_gl_bin")
  if [ "$_gl_before" != "$_gl_after" ]; then
    die_passo 7 "o gitleaks foi reinstalado"
  fi
  if [ "$remote" -eq 0 ]; then
    mirror_new "$_gl_mark" "$T/mirror.log" > "$T/s7/mirror-new.txt"
    while IFS= read -r _line || [ -n "$_line" ]; do
      case "$_line" in
        *" /gitleaks/"*) die_passo 7 "o gitleaks foi baixado de novo" ;;
      esac
    done < "$T/s7/mirror-new.txt"
  fi
  printf 'verify-install: passo 7: tempo %s s\n' "$_secs"
  ok 7
}

step_8() {
  mkdir -p "$T/s8/home" "$T/s8/tmp" "$T/s8/proj" \
    || die_passo 8 "não consegui criar o projeto"
  new_project "$T/s8/proj" || die_passo 8 "não consegui criar o projeto"
  (
    cd "$T/s8/proj" || exit 1
    mkdir -p .agents/skills/outra node_modules/vitest .bob || exit 1
    printf '%s\n' 'node_modules/' > .gitignore || exit 1
    printf '%s\n' '# outra' > .agents/skills/outra/SKILL.md || exit 1
    printf '%s\n' \
      '{"name": "app", "private": true, "devDependencies": {"vitest": "4.1.0"}}' \
      > package.json || exit 1
    printf '%s\n' '{"name": "vitest", "version": "4.1.0"}' \
      > node_modules/vitest/package.json || exit 1
    printf '%s\n' 'base: origin/main' 'paths:' '  include: [src]' \
      > bob.yaml || exit 1
    printf '%s\n' '# waivers do dev' > .bob/waivers.yaml || exit 1
    printf '%s\n' '#!/bin/sh' '# hook do dev' 'exit 0' \
      > .git/hooks/pre-push || exit 1
    chmod 0755 .git/hooks/pre-push || exit 1
    git add -A || exit 1
    git commit -qm fixture || exit 1
  ) || die_passo 8 "não consegui criar o projeto"
  _files='.agents/skills/outra/SKILL.md package.json node_modules/vitest/package.json'
  _files="$_files bob.yaml .bob/waivers.yaml"
  _files="$_files .git/hooks/pre-push"
  for _rel in $_files; do
    file_sha "$T/s8/proj/$_rel" > "$T/s8/sha-$(printf '%s' "$_rel" | tr '/' '_')"
  done
  release_pair
  run_oneliner 8 "$T/s8/home" "$T/s8/tmp" "$T/s8/proj" \
    "$REL_ENV" "$REL_URL" "$(tool_path)" "$T/s8/out.log" "$T/s8/err.log"
  _rc=$?
  if [ "$_rc" -ne 0 ]; then
    die_passo 8 "saiu $_rc; veja $T/s8/out.log"
  fi
  for _rel in $_files; do
    _key=$(printf '%s' "$_rel" | tr '/' '_')
    _before=$(cat "$T/s8/sha-$_key")
    _after=$(file_sha "$T/s8/proj/$_rel")
    if [ "$_before" != "$_after" ]; then
      die_passo 8 "$_rel mudou"
    fi
  done
  if ! grep -Fx '  preserved: .agents/skills/outra (not from bob)' \
    "$T/s8/out.log" >/dev/null 2>&1; then
    die_passo 8 "o resumo não lista .agents/skills/outra"
  fi
  if ! grep -Fx '  preserved: bob.yaml (already exists; not changed)' \
    "$T/s8/out.log" >/dev/null 2>&1; then
    die_passo 8 "o resumo não lista bob.yaml"
  fi
  if ! grep -Fx '  preserved: .bob/waivers.yaml (bob does not change it)' \
    "$T/s8/out.log" >/dev/null 2>&1; then
    die_passo 8 "o resumo não lista .bob/waivers.yaml"
  fi
  if ! grep -Fx \
    '  preserved: .git/hooks/pre-push (pre-push hook without the bob marker)' \
    "$T/s8/out.log" >/dev/null 2>&1; then
    die_passo 8 "o resumo não lista o hook pre-push"
  fi
  _warn="bob setup: hook: warning: existing pre-push hook preserved (.git/hooks/pre-push)."
  _warn="$_warn To use bob's, add: $T/s8/home/.local/share/bob-quality/bin/bob"
  _warn="$_warn check --gates crap,dry,deps."
  if ! grep -Fx "$_warn" "$T/s8/out.log" >/dev/null 2>&1; then
    die_passo 8 "falta o aviso do hook pre-push"
  fi
  _last=$(last_nonempty "$T/s8/out.log")
  if [ "$_last" != "  bob doctor: 0" ]; then
    die_passo 8 "a última linha não é \"  bob doctor: 0\""
  fi
  _vitest=$(bob_vitest)
  _saw=0
  while IFS= read -r _line || [ -n "$_line" ]; do
    case "$_line" in
      *'found 4.1.0'*) die_passo 8 "o doctor viu o vitest do projeto" ;;
    esac
    case "$_line" in
      vitest\ *)
        case "$_line" in
          *"$_vitest"*) _saw=1 ;;
        esac
        ;;
    esac
  done < "$T/s8/out.log"
  if [ "$_saw" -ne 1 ]; then
    die_passo 8 "o doctor viu o vitest do projeto"
  fi
  ok 8
}

step_9a() {
  if [ "$remote" -eq 1 ]; then
    printf '%s\n' 'verify-install: passo 9a: não se aplica (VERIFY_REMOTE=1)'
    return 0
  fi
  mkdir -p "$T/s9a/home" "$T/s9a/tmp" "$T/s9a/proj" \
    || die_passo 9a "não consegui criar o projeto"
  new_project "$T/s9a/proj" || die_passo 9a "não consegui criar o projeto"
  digest "$T/s9a/proj" > "$T/s9a/before.txt" || die_passo 9a "o projeto mudou:"
  release_pair
  GL_URL=$BASE/gitleaks-bad
  _mark=$(line_count "$T/mirror.log")
  run_oneliner 9a "$T/s9a/home" "$T/s9a/tmp" "$T/s9a/proj" \
    "$REL_ENV" "$REL_URL" "$(tool_path)" "$T/s9a/out.log" "$T/s9a/err.log"
  _rc=$?
  if [ "$_rc" -ne 4 ]; then
    die_passo 9a "saiu $_rc com gitleaks adulterado"
  fi
  _cited=0
  while IFS= read -r _line || [ -n "$_line" ]; do
    case "$_line" in
      "bob setup: gitleaks:"*)
        case "$_line" in
          *sha256*) _cited=1 ;;
        esac
        ;;
    esac
  done < "$T/s9a/err.log"
  if [ "$_cited" -eq 0 ]; then
    die_passo 9a "stderr não cita gitleaks e sha256"
  fi
  if [ -e "$T/s9a/home/.local/share/bob-quality/tools/gitleaks" ] \
    || [ -L "$T/s9a/home/.local/share/bob-quality/tools/gitleaks" ]; then
    die_passo 9a "tools/gitleaks foi criado"
  fi
  if [ -e "$T/s9a/home/.local/share/bob-quality/bin/gitleaks" ] \
    || [ -L "$T/s9a/home/.local/share/bob-quality/bin/gitleaks" ]; then
    die_passo 9a "bin/gitleaks foi criado"
  fi
  _last=$(last_nonempty "$T/s9a/out.log")
  if [ "$_last" != "  bob doctor: not run" ]; then
    die_passo 9a "a última linha não é \"  bob doctor: not run\""
  fi
  mirror_new "$_mark" "$T/mirror.log" > "$T/s9a/mirror-new.txt"
  _got=
  while IFS= read -r _line || [ -n "$_line" ]; do
    case "$_line" in
      *" /gitleaks"*)
        if [ -n "$_got" ]; then
          _got="$_got
$_line"
        else
          _got=$_line
        fi
        ;;
    esac
  done < "$T/s9a/mirror-new.txt"
  if [ "$_got" != "GET /gitleaks-bad/$GL_ASSET 200" ]; then
    _flat=$(printf '%s' "$_got" | tr '\n' ',' | sed 's/,$//')
    die_passo 9a "pedidos de gitleaks ao espelho: $_flat"
  fi
  digest "$T/s9a/proj" > "$T/s9a/after.txt" || die_passo 9a "o projeto mudou:"
  if ! cmp -s "$T/s9a/before.txt" "$T/s9a/after.txt"; then
    _diff=$(first_diff "$T/s9a/before.txt" "$T/s9a/after.txt")
    die_passo 9a "o projeto mudou: $_diff"
  fi
  ok 9a
}

step_9b() {
  if [ "$remote" -eq 1 ]; then
    printf '%s\n' 'verify-install: passo 9b: não se aplica (VERIFY_REMOTE=1)'
    return 0
  fi
  mkdir -p "$T/s9b/home" "$T/s9b/tmp" "$T/s9b/proj" \
    || die_passo 9b "não consegui criar o projeto"
  new_project "$T/s9b/proj" || die_passo 9b "não consegui criar o projeto"
  digest "$T/s9b/proj" > "$T/s9b/before.txt" || die_passo 9b "o projeto mudou:"
  GL_URL=$BASE/gitleaks
  run_oneliner 9b "$T/s9b/home" "$T/s9b/tmp" "$T/s9b/proj" \
    "$BASE/bad" "$BASE/bad" "$(tool_path)" "$T/s9b/out.log" "$T/s9b/err.log"
  _rc=$?
  if [ "$_rc" -ne 4 ]; then
    die_passo 9b "saiu $_rc com wheel adulterado"
  fi
  if ! cites_integrity "$T/s9b/err.log"; then
    die_passo 9b "stderr não cita integridade"
  fi
  if [ -e "$T/s9b/home/.local/share/bob-quality/versions" ] \
    || [ -L "$T/s9b/home/.local/share/bob-quality/versions" ]; then
    die_passo 9b "versions/ foi criado"
  fi
  digest "$T/s9b/proj" > "$T/s9b/after.txt" || die_passo 9b "o projeto mudou:"
  if ! cmp -s "$T/s9b/before.txt" "$T/s9b/after.txt"; then
    _diff=$(first_diff "$T/s9b/before.txt" "$T/s9b/after.txt")
    die_passo 9b "o projeto mudou: $_diff"
  fi
  ok 9b
}

pytest_pin() {
  sed -n 's/^    "\(pytest==[^"]*\)",$/\1/p' pyproject.toml
}

step_12() {
  _venv=$S2_HOME/.local/share/bob-quality/current/venv
  if [ ! -x "$_venv/bin/python" ]; then
    die_passo 12 "falta o venv do bob"
  fi
  _pin=$(pytest_pin)
  if [ -z "$_pin" ]; then
    die_passo 12 "não achei o pin do pytest no pyproject.toml"
  fi
  mkdir -p "$T/s12/tmp"
  "$_venv/bin/python" -m pip install -q "$_pin" >"$T/s12/pip.log" 2>&1
  _rc=$?
  if [ "$_rc" -ne 0 ]; then
    die_passo 12 "pip install $_pin falhou; veja $T/s12/pip.log"
  fi
  _t0=$(date +%s)
  env -i "HOME=$S2_HOME" "TMPDIR=$T/s12/tmp" LANG=C.UTF-8 \
    "PATH=$_venv/bin:$(tool_path)" \
    "$_venv/bin/python" -m pytest -q -p no:cacheprovider tests/test_hook.py \
    >"$T/s12/pytest.log" 2>&1
  _rc=$?
  _t1=$(date +%s)
  if [ "$_rc" -ne 0 ]; then
    die_passo 12 "tests/test_hook.py saiu $_rc; veja $T/s12/pytest.log"
  fi
  if ! grep -F '7 passed' "$T/s12/pytest.log" >/dev/null 2>&1; then
    die_passo 12 "tests/test_hook.py não rodou os 7 testes"
  fi
  printf 'verify-install: passo 12: tempo %s s\n' "$((_t1 - _t0))"
  ok 12
}

run_selected() {
  for _id in $STEP_IDS; do
    _wanted=0
    for _pick in $selected; do
      if [ "$_pick" = "$_id" ]; then
        _wanted=1
      fi
    done
    if [ "$_wanted" -eq 0 ]; then
      continue
    fi
    case "$_id" in
      3|4|5|6|7|12) ensure_2 ;;
    esac
    case "$_id" in
      1) step_1 ;;
      2) ensure_2 ;;
      3) step_3 ;;
      4) step_4 ;;
      5) step_5 ;;
      6) step_6 ;;
      7) step_7 ;;
      8) step_8 ;;
      9a) step_9a ;;
      9b) step_9b ;;
      12) step_12 ;;
    esac
  done
}

main() {
  trap cleanup EXIT
  if [ "${VERIFY_REMOTE:-}" = 1 ]; then
    remote=1
  fi
  parse_args "$@"
  if [ ! -f scripts/install.sh ]; then
    die_usage "rode na raiz do checkout do bob (não achei scripts/install.sh)."
  fi
  prepare
  run_selected
}

main "$@"
