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
"$py" -m pip install --disable-pip-version-check "$spec"
