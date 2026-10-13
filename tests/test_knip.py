from __future__ import annotations

from pathlib import Path

import pytest

from bob_quality.adapters.knip import KnipParseError, typescript_symbols
from bob_quality.messages import reason, render
from bob_quality.models import TypeScriptDead

_EXPORT = """\
{"issues":[{"file":"src/app/orphan.ts","exports":[{"name":"orphan","line":3,"col":1,"pos":10}],"dependencies":[{"name":"left-pad"}],"files":["src/gone.ts"]}]}
"""

_KINDS = """\
{
  "issues": [
    {
      "file": "./src/app/api.ts",
      "exports": [{"name": "orphan", "line": 3, "col": 1, "pos": 10}],
      "types": [{"name": "Id", "line": 5}],
      "enumMembers": [{"name": "Red", "namespace": "Colors", "line": 8}],
      "namespaceMembers": [{"name": "helper", "namespace": "Util", "line": 9}],
      "nsExports": [{"name": "open", "line": 10}],
      "nsTypes": [{"name": "Mode", "namespace": "Net", "line": 11}],
      "dependencies": [{"name": "left-pad"}],
      "devDependencies": [],
      "duplicates": [[{"name": "a"}]],
      "cycles": [],
      "binaries": [{"name": "bob"}],
      "unlisted": [{"name": "lodash"}],
      "unresolved": [{"name": "missing"}],
      "files": ["src/gone.ts"]
    }
  ]
}
"""


def test_a_knip_export_becomes_one_symbol(tmp_path: Path) -> None:
    assert typescript_symbols(_EXPORT, tmp_path) == (
        TypeScriptDead("src/app/orphan.ts", 3, "orphan", "export"),
    )


def test_symbol_keys_keep_their_kind_and_other_keys_are_ignored(tmp_path: Path) -> None:
    assert typescript_symbols(_KINDS, tmp_path) == (
        TypeScriptDead("src/app/api.ts", 3, "orphan", "export"),
        TypeScriptDead("src/app/api.ts", 5, "Id", "type"),
        TypeScriptDead("src/app/api.ts", 8, "Colors.Red", "enum_member"),
        TypeScriptDead("src/app/api.ts", 9, "Util.helper", "namespace_member"),
        TypeScriptDead("src/app/api.ts", 10, "open", "ns_export"),
        TypeScriptDead("src/app/api.ts", 11, "Net.Mode", "ns_type"),
    )


def test_a_path_outside_the_repo_is_omitted(tmp_path: Path) -> None:
    raw = """\
{"issues":[
  {"file":"/etc/passwd.ts","exports":[{"name":"secret","line":1}]},
  {"file":"src/app/orphan.ts","exports":[{"name":"orphan","line":3}]}
]}
"""

    assert typescript_symbols(raw, tmp_path) == (
        TypeScriptDead("src/app/orphan.ts", 3, "orphan", "export"),
    )


def test_an_empty_issue_list_has_no_symbols(tmp_path: Path) -> None:
    assert typescript_symbols('{"issues":[]}\n', tmp_path) == ()


@pytest.mark.parametrize(
    "raw",
    [
        "not json",
        "[]",
        "{}",
        '{"issues":{}}',
        '{"issues":[1]}',
        '{"issues":[{"exports":[]}]}',
        '{"issues":[{"file":"src/a.ts","exports":"nope"}]}',
        '{"issues":[{"file":"src/a.ts","exports":[{"line":3}]}]}',
        '{"issues":[{"file":"src/a.ts","exports":[{"name":"x"}]}]}',
        '{"issues":[{"file":"src/a.ts","exports":[{"name":"x","line":0}]}]}',
        '{"issues":[{"file":"src/a.ts","exports":[{"name":"x","line":true}]}]}',
        '{"issues":[{"file":"src/a.ts","exports":[{"name":"x","line":1.5}]}]}',
        '{"issues":[{"file":"src/a.ts","exports":[{"name":"x","line":"3"}]}]}',
        '{"issues":[{"file":"/etc/x.ts","exports":[{"name":"x","line":true}]}]}',
        '{"issues":[{"file":"src/a.ts","types":[{"name":"T","namespace":1,"line":2}]}]}',
    ],
)
def test_a_broken_document_rejects_every_symbol(tmp_path: Path, raw: str) -> None:
    with pytest.raises(KnipParseError) as caught:
        typescript_symbols(raw, tmp_path)

    assert render(reason(caught.value), "en") == "knip: output could not be parsed"
    assert render(reason(caught.value), "pt-BR") == "knip: saída ilegível"
