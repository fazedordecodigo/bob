"""O show só preenche o diff. O status, e portanto o veredito, sai do results."""

from __future__ import annotations

from pathlib import Path

import bob_quality.mutate as mutate_module
from bob_quality.models import CyclomaticFunction
from bob_quality.mutate import _run_and_parse

RESULTS = """\
    app.weak.x_classify__mutmut_1: survived
    app.weak.x_classify__mutmut_2: killed
    app.weak.x_classify__mutmut_3: timeout
    app.weak.x_classify__mutmut_4: no tests
"""

SHOW = """\
--- src/app/weak.py
+++ src/app/weak.py
@@ -2 +2 @@
-old
+new
"""


def test_show_runs_only_for_survivors_and_timeouts(monkeypatch) -> None:
    shown: list[str] = []

    def fake_show(_cwd, mutant_id: str) -> str:
        shown.append(mutant_id)
        return SHOW

    monkeypatch.setattr(mutate_module, "run_mutmut", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(mutate_module, "mutmut_results", lambda _cwd: RESULTS)
    monkeypatch.setattr(mutate_module, "mutmut_show", fake_show)
    remutate = [
        CyclomaticFunction(
            file="src/app/weak.py", name="classify", start_line=1, end_line=4, cc=1
        )
    ]

    parsed, failed = _run_and_parse(Path("."), remutate, None, {}, [])

    assert failed is None
    assert shown == [
        "app.weak.x_classify__mutmut_1",
        "app.weak.x_classify__mutmut_3",
    ]
    by_id = {item.id: item for item in parsed}
    assert by_id["app.weak.x_classify__mutmut_1"].status == "survived"
    assert by_id["app.weak.x_classify__mutmut_1"].operator == "old -> new"
    assert by_id["app.weak.x_classify__mutmut_2"].status == "killed"
    assert by_id["app.weak.x_classify__mutmut_2"].operator == ""
    assert by_id["app.weak.x_classify__mutmut_3"].status == "timeout"
    assert by_id["app.weak.x_classify__mutmut_3"].operator == "old -> new"
    assert by_id["app.weak.x_classify__mutmut_4"].status == "no_coverage"
    assert by_id["app.weak.x_classify__mutmut_4"].operator == ""
