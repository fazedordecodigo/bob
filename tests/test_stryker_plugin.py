"""Reescrita do join de collectTestName para o Vitest 5.

O runner 10.0.0 junta o nome com espaço. O Vitest 5 casa testNamePattern
com ' > '. A função exportada é o que o plugin aplica nos dois arquivos.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

PLUGIN = (
    Path(__file__).resolve().parents[1]
    / "src"
    / "bob_quality"
    / "js"
    / "stryker-vitest5-plugin.mjs"
)

_PROBE = """
const { rewriteSetup } = await import(process.env.PLUGIN);
const space = "return nameParts.join(' ').trim();";
const arrow = "return nameParts.join(' > ').trim();";
const both = arrow + "\\n" + space;
let threw = false;
try {
  rewriteSetup("return nameParts.join('-').trim();");
} catch (error) {
  threw = error instanceof Error;
}
console.log(JSON.stringify({
  space: rewriteSetup(space),
  arrow: rewriteSetup(arrow),
  both: rewriteSetup(both),
  threw,
}));
"""


def test_rewrite_setup_switches_the_space_join_and_keeps_an_arrow_join() -> None:
    completed = subprocess.run(
        ["node", "--input-type=module", "-e", _PROBE],
        capture_output=True,
        text=True,
        env={**os.environ, "PLUGIN": PLUGIN.as_uri()},
    )

    assert completed.returncode == 0, completed.stderr
    assert json.loads(completed.stdout) == {
        "space": "return nameParts.join(' > ').trim();",
        "arrow": "return nameParts.join(' > ').trim();",
        "both": "return nameParts.join(' > ').trim();\nreturn nameParts.join(' ').trim();",
        "threw": True,
    }
