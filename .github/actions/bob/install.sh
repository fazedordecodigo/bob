#!/usr/bin/env bash
# Instala o bob a partir do requisito impresso por resolve_install.py.
set -euo pipefail

script_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
if command -v python >/dev/null 2>&1; then
  py=python
else
  py=python3
fi

spec=$("$py" "$script_dir/resolve_install.py")
if [[ "$spec" == ".[dev]" ]]; then
  "$py" -m pip install --disable-pip-version-check -e "$spec"
else
  "$py" -m pip install --disable-pip-version-check "$spec"
fi
"$py" -m pip install --disable-pip-version-check 'uv==0.13.0'
