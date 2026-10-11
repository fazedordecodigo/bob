#!/usr/bin/env bash
# Repete o exit code gravado por run_check.sh. Sem o arquivo, é erro de config.
set -u

exit_file="${BOB_EXIT_FILE:-.bob/exit-code}"
if [[ ! -f "$exit_file" ]]; then
  echo "exit code do bob ausente" >&2
  exit 4
fi

code=$(tr -d '[:space:]' <"$exit_file")
exit "$code"
