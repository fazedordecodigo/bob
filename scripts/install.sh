#!/bin/sh
# bob install.sh: comando único (CT2). POSIX sh; sem bashismos.
set -u
STEPS='projeto plataforma python node ferramentas versão download integridade pacote launcher perfil setup'
PROFILE_LINE='export PATH="$HOME/.local/bin:$PATH" # managed-by: bob-quality'
DEFAULT_API='https://api.github.com/repos/fazedordecodigo/bob/releases/latest'
DEFAULT_DOWNLOAD='https://github.com/fazedordecodigo/bob/releases/download'
CURL_OPTS='-fsSL --connect-timeout 15 --max-time 300 --retry 2'
PIP_OPTS='--disable-pip-version-check --no-input'
NODE_FLOOR='22.18.0'
NODE_BELOW='23'
PYTHON_FLOOR='3.10'

resolve_bob_home() {
  _chosen=${BOB_HOME:-}
  case "$_chosen" in
    */) _chosen=${_chosen%/} ;;
  esac
  if [ -n "$_chosen" ]; then
    case "$_chosen" in
      /*)
        printf '%s' "$_chosen"
        return 0
        ;;
      *)
        return 1
        ;;
    esac
  fi
  _data=${XDG_DATA_HOME:-}
  case "$_data" in
    */) _data=${_data%/} ;;
  esac
  case "$_data" in
    /*)
      printf '%s' "$_data/bob-quality"
      return 0
      ;;
  esac
  printf '%s' "${HOME:-}/.local/share/bob-quality"
  return 0
}

say() {
  _id=$1
  shift
  _p1=${1-}
  _p2=${2-}
  _use_lang=$bob_lang
  if [ "$_id" = "usage_lang_invalid" ]; then
    _use_lang=en
  fi
  _major=${NODE_FLOOR%%.*}
  if [ "$_use_lang" = "pt-BR" ]; then
    case "$_id" in
      usage_unknown)
        _msg="install: uso: argumento desconhecido $_p1. Rode com --help." ;;
      usage_lang_value)
        _msg="install: uso: --lang precisa de um valor (en ou pt-BR). Rode com --help." ;;
      bob_home_relative)
        _msg="install: launcher: BOB_HOME=$_p1 precisa ser absoluto. Use um caminho absoluto." ;;
      git_missing)
        _msg="install: projeto: git não encontrado. Instale o git e rode de novo." ;;
      not_root)
        _msg="install: projeto: $_p1 não é a raiz de um repositório git. Rode na raiz do projeto." ;;
      platform)
        _msg="install: plataforma: $_p1/$_p2 não é suportada. Suportadas: Linux e macOS, x64 e arm64." ;;
      python_missing)
        _msg="install: python: python3 não encontrado. Instale um Python $PYTHON_FLOOR ou mais novo." ;;
      python_old)
        _msg="install: python: encontrado $_p1, exigido >=$PYTHON_FLOOR. Instale um Python $PYTHON_FLOOR ou mais novo." ;;
      python_venv)
        _msg="install: python: o módulo venv não está disponível. No Ubuntu, instale o pacote python3-venv." ;;
      node_missing)
        _msg="install: node: node não encontrado, exigido >=$NODE_FLOOR <$NODE_BELOW. Instale o Node $NODE_FLOOR ou mais novo da linha $_major." ;;
      node_out)
        _msg="install: node: encontrado $_p1, exigido >=$NODE_FLOOR <$NODE_BELOW. Instale o Node $NODE_FLOOR ou mais novo da linha $_major." ;;
      npm_missing)
        _msg="install: node: npm não encontrado. Instale o npm junto com o Node e rode de novo." ;;
      tool_missing)
        _msg="install: ferramentas: $_p1 não encontrado. Instale $_p1 e rode de novo." ;;
      url_not_allowed)
        _msg="install: versão: BOB_RELEASES_URL=$_p1 não é permitida. Use https://, ou http:// só em 127.0.0.1 ou localhost." ;;
      tmp_failed)
        _msg="install: versão: não consegui criar uma pasta temporária em $_p1. Confira o TMPDIR." ;;
      version_invalid)
        _msg="install: versão: BOB_VERSION=$_p1 inválida. Use vX.Y.Z." ;;
      api_failed)
        _msg="install: versão: não consegui ler a última release ($_p1). Tente de novo mais tarde." ;;
      download_failed)
        _msg="install: download: $_p1 falhou ($_p2). Confira a rede e tente de novo." ;;
      download_missing)
        _msg="install: download: a release $_p1 está incompleta ($_p2 ausente). Abra uma issue." ;;
      integrity)
        _msg="install: integridade: o sha256 de $_p1 não confere. Nada foi instalado. Tente de novo." ;;
      pip_failed)
        _msg="install: pacote: pip falhou. Veja a saída acima e tente de novo." ;;
      launcher_failed)
        _msg="install: launcher: não consegui criar $_p1 ($_p2). Confira as permissões." ;;
      launcher_warning)
        _msg="install: launcher: aviso: $_p1 já existe e não é do bob; ficou como está." ;;
      profile_warning)
        _msg="install: perfil: aviso: não consegui gravar $_p1 ($_p2). "
        _msg="${_msg}Para usar o comando bob, acrescente ao seu perfil: "
        _msg="${_msg}${PROFILE_LINE%% #*}." ;;
    esac
  else
    case "$_id" in
      usage_unknown)
        _msg="install: usage: unknown argument $_p1. Run with --help." ;;
      usage_lang_value)
        _msg="install: usage: --lang needs a value (en or pt-BR). Run with --help." ;;
      usage_lang_invalid)
        _msg="install: usage: invalid language $_p1. Use en or pt-BR." ;;
      bob_home_relative)
        _msg="install: launcher: BOB_HOME=$_p1 must be absolute. Use an absolute path." ;;
      git_missing)
        _msg="install: projeto: git not found. Install git and run again." ;;
      not_root)
        _msg="install: projeto: $_p1 is not the root of a git repository. Run in the project root." ;;
      platform)
        _msg="install: plataforma: $_p1/$_p2 is not supported. Supported: Linux and macOS, x64 and arm64." ;;
      python_missing)
        _msg="install: python: python3 not found. Install Python $PYTHON_FLOOR or newer." ;;
      python_old)
        _msg="install: python: found $_p1, required >=$PYTHON_FLOOR. Install Python $PYTHON_FLOOR or newer." ;;
      python_venv)
        _msg="install: python: the venv module is not available. On Ubuntu, install the python3-venv package." ;;
      node_missing)
        _msg="install: node: node not found, required >=$NODE_FLOOR <$NODE_BELOW. Install Node $NODE_FLOOR or newer from the $_major line." ;;
      node_out)
        _msg="install: node: found $_p1, required >=$NODE_FLOOR <$NODE_BELOW. Install Node $NODE_FLOOR or newer from the $_major line." ;;
      npm_missing)
        _msg="install: node: npm not found. Install npm with Node and run again." ;;
      tool_missing)
        _msg="install: ferramentas: $_p1 not found. Install $_p1 and run again." ;;
      url_not_allowed)
        _msg="install: versão: BOB_RELEASES_URL=$_p1 is not allowed. Use https://, or http:// only on 127.0.0.1 or localhost." ;;
      tmp_failed)
        _msg="install: versão: could not create a temporary folder in $_p1. Check TMPDIR." ;;
      version_invalid)
        _msg="install: versão: BOB_VERSION=$_p1 is invalid. Use vX.Y.Z." ;;
      api_failed)
        _msg="install: versão: could not read the latest release ($_p1). Try again later." ;;
      download_failed)
        _msg="install: download: $_p1 failed ($_p2). Check the network and try again." ;;
      download_missing)
        _msg="install: download: release $_p1 is incomplete ($_p2 missing). Open an issue." ;;
      integrity)
        _msg="install: integridade: the sha256 of $_p1 does not match. Nothing was installed. Try again." ;;
      pip_failed)
        _msg="install: pacote: pip failed. See the output above and try again." ;;
      launcher_failed)
        _msg="install: launcher: could not create $_p1 ($_p2). Check the permissions." ;;
      launcher_warning)
        _msg="install: launcher: warning: $_p1 already exists and is not bob's; left as is." ;;
      profile_warning)
        _msg="install: perfil: warning: could not write $_p1 ($_p2). "
        _msg="${_msg}To use the bob command, add to your profile: "
        _msg="${_msg}${PROFILE_LINE%% #*}." ;;
    esac
  fi
  if [ "$_id" = "launcher_warning" ] || [ "$_id" = "profile_warning" ]; then
    printf '%s\n' "$_msg"
  else
    printf '%s\n' "$_msg" >&2
  fi
}

fail() {
  say "$@"
  exit 4
}

step_ok() {
  printf 'install: %s: ok\n' "$1"
}

_print_help() {
  if [ "$bob_lang" = "pt-BR" ]; then
    printf '%s\n' "Uso: sh install.sh [--lang en|pt-BR] [--help]"
    printf '%s\n' "Instala o bob para este usuário e o prepara no projeto atual (rode na raiz do projeto git)."
    printf '%s\n' "Precisa de: git, python3 >=$PYTHON_FLOOR com venv, node >=$NODE_FLOOR <$NODE_BELOW com npm, curl, sha256sum ou shasum."
  else
    printf '%s\n' "Usage: sh install.sh [--lang en|pt-BR] [--help]"
    printf '%s\n' "Installs bob for this user and sets it up in the current project (run it in the git project root)."
    printf '%s\n' "Needs: git, python3 >=$PYTHON_FLOOR with venv, node >=$NODE_FLOOR <$NODE_BELOW with npm, curl, sha256sum or shasum."
  fi
}

_net_status() {
  _http=$1
  _rc=$2
  if [ -n "$_http" ] && [ "$_http" != "000" ]; then
    printf '%s' "HTTP $_http"
  else
    printf '%s' "curl $_rc"
  fi
}

_tag_ok() {
  printf '%s\n' "$1" | grep -Eq '^v[0-9]+\.[0-9]+\.[0-9]+$'
}

_read_latest() {
  _http=$(curl $CURL_OPTS -H 'Accept: application/vnd.github+json' -w '%{http_code}' -o "$work/latest.json" "$api_url" 2>"$work/curl.err")
  _rc=$?
  if [ "$_rc" -ne 0 ]; then
    fail api_failed "$(_net_status "$_http" "$_rc")"
  fi
  tag=$(python3 -c 'import json, sys
try:
    data = json.load(open(sys.argv[1], encoding="utf-8"))
except Exception:
    data = None
name = data.get("tag_name") if isinstance(data, dict) else None
if not isinstance(name, str):
    raise SystemExit(1)
sys.stdout.write(name)
' "$work/latest.json" 2>/dev/null) || tag=
  if _tag_ok "$tag"; then
    return 0
  fi
  if [ "$bob_lang" = "pt-BR" ]; then
    fail api_failed "resposta inválida"
  fi
  fail api_failed "invalid response"
}

_fetch() {
  _asset=$1
  _url="$dl_base/$tag/$_asset"
  _http=$(curl $CURL_OPTS -w '%{http_code}' -o "$work/$_asset" "$_url" 2>"$work/curl.err")
  _rc=$?
  if [ "$_rc" -ne 0 ]; then
    if [ "$_http" = "404" ]; then
      fail download_missing "$tag" "$_asset"
    fi
    fail download_failed "$_url" "$(_net_status "$_http" "$_rc")"
  fi
}

launcher_try() {
  _lpath=$1
  shift
  if "$@" >"$work/launcher.out" 2>"$work/launcher.err"; then
    return 0
  fi
  _lerr=
  IFS= read -r _lerr < "$work/launcher.err" || _lerr=
  if [ -z "$_lerr" ]; then
    if [ "$bob_lang" = "pt-BR" ]; then
      _lerr="erro desconhecido"
    else
      _lerr="unknown error"
    fi
  fi
  fail launcher_failed "$_lpath" "$_lerr"
}

step_projeto() {
  command -v git >/dev/null 2>&1 || fail git_missing
  _top=$(git rev-parse --show-toplevel 2>/dev/null) || _top=
  _here=$(pwd -P)
  if [ "$_top" != "$_here" ]; then
    fail not_root "$_here"
  fi
  step_ok projeto
}

step_plataforma() {
  _os=$(uname -s)
  _arch=$(uname -m)
  case "$_os" in
    Linux|Darwin) ;;
    *) fail platform "$_os" "$_arch" ;;
  esac
  case "$_arch" in
    x86_64|amd64|aarch64|arm64) ;;
    *) fail platform "$_os" "$_arch" ;;
  esac
  step_ok plataforma
}

step_python() {
  command -v python3 >/dev/null 2>&1 || fail python_missing
  _found=$(python3 -c 'import sys; print("%d.%d.%d" % sys.version_info[:3])') || _found=
  awk -v found="$_found" -v floor="$PYTHON_FLOOR" 'BEGIN {
    split(found, a, ".")
    split(floor, f, ".")
    if ((a[1] + 0) < (f[1] + 0)) exit 1
    if ((a[1] + 0) == (f[1] + 0) && (a[2] + 0) < (f[2] + 0)) exit 1
    exit 0
  }' || fail python_old "$_found"
  python3 -c 'import venv, ensurepip' 2>/dev/null || fail python_venv
  step_ok python
}

step_node() {
  _major=${NODE_FLOOR%%.*}
  command -v node >/dev/null 2>&1 || fail node_missing
  _found=$(node --version) || _found=
  if ! _tag_ok "$_found"; then
    fail node_out "$_found"
  fi
  _bare=${_found#v}
  awk -v v="$_bare" -v floor="$NODE_FLOOR" -v below="$NODE_BELOW" 'BEGIN {
    split(v, a, ".")
    split(floor, f, ".")
    if ((a[1] + 0) >= (below + 0)) exit 1
    for (i = 1; i <= 3; i++) {
      av = a[i] + 0
      fv = f[i] + 0
      if (av > fv) exit 0
      if (av < fv) exit 1
    }
    exit 0
  }' || fail node_out "$_found"
  command -v npm >/dev/null 2>&1 || fail npm_missing
  step_ok node
}

step_ferramentas() {
  command -v curl >/dev/null 2>&1 || fail tool_missing curl
  if command -v sha256sum >/dev/null 2>&1; then
    sha_cmd=sha256sum
  elif command -v shasum >/dev/null 2>&1; then
    sha_cmd=shasum
  else
    fail tool_missing sha256sum
  fi
  step_ok ferramentas
}

step_versao() {
  _rel=${BOB_RELEASES_URL:-}
  if [ -n "$_rel" ]; then
    case "$_rel" in
      */) _rel=${_rel%/} ;;
    esac
    case "$_rel" in
      https://*|http://127.0.0.1|http://127.0.0.1[:/]*|http://localhost|http://localhost[:/]*)
        ;;
      *)
        fail url_not_allowed "$_rel"
        ;;
    esac
    api_url="$_rel/api/releases/latest"
    dl_base="$_rel/download"
  else
    api_url=$DEFAULT_API
    dl_base=$DEFAULT_DOWNLOAD
  fi
  _tmp_parent=${TMPDIR:-/tmp}
  work=$(mktemp -d "$_tmp_parent/bob-install.XXXXXX") || fail tmp_failed "$_tmp_parent"
  trap 'rm -rf "$work"' EXIT INT TERM
  _pinned=${BOB_VERSION:-}
  if [ -n "$_pinned" ]; then
    _tag_ok "$_pinned" || fail version_invalid "$_pinned"
    tag=$_pinned
  else
    _read_latest
  fi
  printf 'install: versão: %s\n' "$tag"
}

step_download() {
  whl="bob_quality-${tag#v}-py3-none-any.whl"
  _fetch "$whl"
  _fetch SHA256SUMS
  step_ok download
}

step_integridade() {
  want=$(awk -v f="$whl" '$2 == f { print $1; exit }' "$work/SHA256SUMS") || want=
  if [ "$sha_cmd" = "sha256sum" ]; then
    got=$(sha256sum "$work/$whl" | awk '{ print $1 }')
  else
    got=$(shasum -a 256 "$work/$whl" | awk '{ print $1 }')
  fi
  if [ -z "$want" ] || [ "$want" != "$got" ]; then
    fail integrity "$whl"
  fi
  step_ok integridade
}

step_pacote() {
  _vd="$bob_root/versions/${tag#v}"
  _have=
  if [ -f "$_vd/.complete" ]; then
    IFS= read -r _have < "$_vd/.complete" || _have=
  fi
  if [ -n "$got" ] && [ "$_have" = "$got" ]; then
    step_ok pacote
    return 0
  fi
  rm -rf "$_vd" || fail pip_failed
  mkdir -p "$_vd" || { rm -rf "$_vd"; fail pip_failed; }
  python3 -m venv "$_vd/venv" || { rm -rf "$_vd"; fail pip_failed; }
  "$_vd/venv/bin/python" -m pip install $PIP_OPTS "$work/$whl" || {
    rm -rf "$_vd"
    fail pip_failed
  }
  printf '%s\n' "$got" > "$_vd/.complete" || { rm -rf "$_vd"; fail pip_failed; }
  step_ok pacote
}

step_launcher() {
  _local="$HOME/.local/bin"
  _link="$_local/bob"
  _vd="$bob_root/versions/${tag#v}"
  launcher_try "$bob_root/bin" mkdir -p "$bob_root/bin"
  launcher_try "$_local" mkdir -p "$_local"
  launcher_try "$bob_root/current.tmp" rm -f "$bob_root/current.tmp"
  launcher_try "$bob_root/current.tmp" ln -s "versions/${tag#v}" "$bob_root/current.tmp"
  launcher_try "$bob_root/current" \
    "$_vd/venv/bin/python" -c 'import os, sys; os.replace(sys.argv[1], sys.argv[2])' \
    "$bob_root/current.tmp" "$bob_root/current"
  launcher_try "$bob_root/bin/bob" ln -sfn ../current/venv/bin/bob "$bob_root/bin/bob"
  if [ -L "$_link" ] && [ "$(readlink "$_link")" = "$bob_root/bin/bob" ]; then
    :
  elif [ -e "$_link" ] || [ -L "$_link" ]; then
    say launcher_warning "$_link"
  else
    launcher_try "$_link" ln -s "$bob_root/bin/bob" "$_link"
  fi
  step_ok launcher
}

step_perfil() {
  case ":${PATH:-}:" in
    *":$HOME/.local/bin:"*)
      BOB_INSTALL_PROFILE=already-on-path
      step_ok perfil
      return 0
      ;;
  esac
  _sh=${SHELL:-}
  case "${_sh##*/}" in
    zsh) _pf=${ZDOTDIR:-$HOME}/.zshrc ;;
    bash) _pf=$HOME/.bashrc ;;
    *) _pf=$HOME/.profile ;;
  esac
  _mark="#${PROFILE_LINE#* #}"
  if [ -f "$_pf" ] && grep -qF "$_mark" "$_pf"; then
    BOB_INSTALL_PROFILE="already-marked:$_pf"
    step_ok perfil
    return 0
  fi
  _pok=0
  if [ -e "$_pf" ]; then
    _last=$(tail -c 1 "$_pf" 2>"$work/perfil.err") || _pok=1
    if [ "$_pok" -eq 0 ]; then
      if [ -n "$_last" ]; then
        { printf '\n%s\n' "$PROFILE_LINE"; } 2>"$work/perfil.err" >>"$_pf" || _pok=1
      else
        { printf '%s\n' "$PROFILE_LINE"; } 2>"$work/perfil.err" >>"$_pf" || _pok=1
      fi
    fi
  else
    { printf '%s\n' "$PROFILE_LINE"; } 2>"$work/perfil.err" >"$_pf" \
      && chmod 0644 "$_pf" 2>"$work/perfil.err" || _pok=1
  fi
  if [ "$_pok" -eq 0 ]; then
    BOB_INSTALL_PROFILE=$_pf
  else
    _perr=
    IFS= read -r _perr < "$work/perfil.err" || _perr=
    _perr=${_perr##*: }
    if [ -z "$_perr" ]; then
      if [ "$bob_lang" = "pt-BR" ]; then
        _perr="erro desconhecido"
      else
        _perr="unknown error"
      fi
    fi
    say profile_warning "$_pf" "$_perr"
    BOB_INSTALL_PROFILE="failed:$_pf"
  fi
  step_ok perfil
}

step_setup() {
  rm -rf "$work"
  trap - EXIT INT TERM
  export BOB_INSTALL_PROFILE
  exec "$bob_root/bin/bob" setup --lang "$bob_lang" </dev/null
  exit $?
}

_run_step() {
  case "$1" in
    projeto) step_projeto ;;
    plataforma) step_plataforma ;;
    python) step_python ;;
    node) step_node ;;
    ferramentas) step_ferramentas ;;
    versão) step_versao ;;
    download) step_download ;;
    integridade) step_integridade ;;
    pacote) step_pacote ;;
    launcher) step_launcher ;;
    perfil) step_perfil ;;
    setup) step_setup ;;
    *) exit 4 ;;
  esac
}

main() {
  bob_lang=${BOB_LANG:-en}
  _help=0
  while [ "$#" -gt 0 ]; do
    case "$1" in
      --help)
        _help=1
        shift
        ;;
      --lang)
        if [ "$#" -lt 2 ]; then
          fail usage_lang_value
        fi
        bob_lang=$2
        shift 2
        ;;
      *)
        fail usage_unknown "$1"
        ;;
    esac
  done
  case "$bob_lang" in
    en|pt-BR) ;;
    *) fail usage_lang_invalid "$bob_lang" ;;
  esac
  if [ "$_help" -eq 1 ]; then
    _print_help
    exit 0
  fi
  bob_root=$(resolve_bob_home) || fail bob_home_relative "${BOB_HOME:-}"
  for _step in $STEPS; do
    _run_step "$_step"
  done
}

main "$@"
