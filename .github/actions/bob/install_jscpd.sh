#!/usr/bin/env bash
set -euo pipefail

version="${JSCPD_VERSION:-5.4.1}"

if command -v python >/dev/null 2>&1; then
  py=python
else
  py=python3
fi

have=$("$py" -c '
from bob_quality.npm_tools import installed_npm_version, npm_prefix
from bob_quality.tools import ToolError
try:
    print(installed_npm_version(npm_prefix(), "jscpd"))
except ToolError:
    print("")
')
if [[ "$have" == "$version" ]]; then
  exit 0
fi

"$py" -c 'from bob_quality.npm_tools import install_npm_dependencies; raise SystemExit(install_npm_dependencies("en"))'

found=$("$py" -c '
from bob_quality.npm_tools import installed_npm_version, npm_prefix
print(installed_npm_version(npm_prefix(), "jscpd"))
')
if [[ "$found" != "$version" ]]; then
  printf 'jscpd %s != %s\n' "$found" "$version" >&2
  exit 1
fi
