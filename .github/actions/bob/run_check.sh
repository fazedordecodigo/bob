#!/usr/bin/env bash
# Roda `bob check` e grava o exit code. Este script sai 0 para o comentário
# e o artefato rodarem mesmo quando o check falha.
set -u

exit_file="${BOB_EXIT_FILE:-.bob/exit-code}"
mkdir -p "$(dirname "$exit_file")" .bob

gates="${BOB_GATES:-crap,dry,deps,mutate}"
base="${BOB_BASE:-}"
if [[ -z "$base" && -n "${GITHUB_BASE_REF:-}" ]]; then
  base="origin/${GITHUB_BASE_REF}"
fi

args=(check --gates "$gates" --format both --out "${BOB_OUT:-.bob/}")
if [[ -n "$base" ]]; then
  args+=(--base "$base")
fi

set +e
bob "${args[@]}"
code=$?
set -e

printf '%s\n' "$code" >"$exit_file"
exit 0
