"""Veredito de complexidade cognitiva no núcleo."""

import json
from pathlib import Path
from typing import get_args

import pytest

from bob_quality.cognitive_gate import _parse_payload
from bob_quality.config import SOURCE_LANGUAGES
from bob_quality.core import cognitive_verdict
from bob_quality.messages import render
from bob_quality.models import CognitiveFunction, CognitiveLanguage


def _function(
    name: str,
    *,
    score: int,
    file: str = "src/app.py",
    start: int = 1,
    end: int = 8,
    language: CognitiveLanguage = "python",
) -> CognitiveFunction:
    return CognitiveFunction(
        file=file,
        name=name,
        start_line=start,
        end_line=end,
        score=score,
        language=language,
    )


def test_cognitive_language_matches_source_languages() -> None:
    assert set(get_args(CognitiveLanguage)) == set(SOURCE_LANGUAGES)


def test_score_at_the_limit_warns_and_one_below_stays_out() -> None:
    at_limit = _function("edge", score=15)
    below = _function("under", score=14, start=10, end=12)
    diff = {"src/app.py": set(range(1, 13))}

    result, found, code = cognitive_verdict([below, at_limit], 15, set(), diff)

    assert result.name == "cognitive"
    assert result.status == "warn"
    assert code == 0
    assert [item.name for item in found] == ["edge"]


def test_unchanged_function_stays_out_when_a_changed_one_warns() -> None:
    changed = _function("touched", score=15, start=1, end=4)
    quiet = _function("legacy", score=15, start=20, end=30)
    diff = {"src/app.py": {2}}

    result, found, code = cognitive_verdict([quiet, changed], 15, set(), diff)

    assert result.status == "warn"
    assert code == 0
    assert [item.name for item in found] == ["touched"]


def test_bare_save_does_not_waive_class_method() -> None:
    method = _function("Foo::save", score=15)
    diff = {"src/app.py": {1}}

    result, found, code = cognitive_verdict(
        [method], 15, {"cognitive:src/app.py:save"}, diff
    )

    assert result.status == "warn"
    assert code == 0
    assert [item.name for item in found] == ["Foo::save"]
    assert found[0].waiver_id() == "cognitive:src/app.py:Foo::save"

    cleared, waived, waived_code = cognitive_verdict(
        [method], 15, {"cognitive:src/app.py:Foo::save"}, diff
    )

    assert cleared.status == "passed"
    assert waived_code == 0
    assert [item.name for item in waived] == []


def test_warning_reason_counts_functions_in_both_languages() -> None:
    one, found, code = cognitive_verdict(
        [_function("edge", score=15)], 15, set(), {"src/app.py": {1}}
    )

    assert code == 0
    assert [item.name for item in found] == ["edge"]
    assert render(one.reason, "en") == "1 function at or above the cognitive limit"
    assert render(one.reason, "pt-BR") == (
        "1 função no limite de complexidade cognitiva ou acima"
    )

    two, found, code = cognitive_verdict(
        [_function("a", score=15), _function("b", score=16, file="src/b.py")],
        15,
        set(),
        {"src/app.py": {1}, "src/b.py": {1}},
    )

    assert code == 0
    assert [item.name for item in found] == ["a", "b"]
    assert render(two.reason, "en") == "2 functions at or above the cognitive limit"
    assert render(two.reason, "pt-BR") == (
        "2 funções no limite de complexidade cognitiva ou acima"
    )


def test_warnings_sort_by_file_then_line_then_name() -> None:
    later = _function("b", score=15, file="src/b.py", start=1, end=2)
    same_line_z = _function("z", score=16, file="src/a.py", start=3, end=4)
    same_line_a = _function("a", score=20, file="src/a.py", start=3, end=4)
    diff = {"src/a.py": {3}, "src/b.py": {1}}

    result, found, code = cognitive_verdict(
        [later, same_line_z, same_line_a], 15, set(), diff
    )

    assert result.status == "warn"
    assert code == 0
    assert [(item.file, item.start_line, item.name) for item in found] == [
        ("src/a.py", 3, "a"),
        ("src/a.py", 3, "z"),
        ("src/b.py", 1, "b"),
    ]


def test_domain_payload_keeps_a_method_and_rejects_eslint_results(tmp_path: Path) -> None:
    raw = json.dumps(
        [
            {
                "file": str(tmp_path / "src" / "foo.ts"),
                "name": "Foo::save",
                "start_line": 2,
                "end_line": 19,
                "score": 15,
            }
        ]
    )

    found = _parse_payload(raw, tmp_path)

    assert [
        (item.file, item.name, item.start_line, item.end_line, item.score, item.language)
        for item in found
    ] == [("src/foo.ts", "Foo::save", 2, 19, 15, "typescript")]
    assert found[0].waiver_id() == "cognitive:src/foo.ts:Foo::save"
    with pytest.raises(ValueError) as caught:
        _parse_payload('[{"filePath": "src/foo.ts", "messages": []}]', tmp_path)
    assert str(caught.value) == "eslint payload is not domain json"


@pytest.mark.parametrize(
    ("file", "name", "start", "end", "score", "message"),
    [
        ("/abs.py", "save", 1, 2, 0, "file must be repo-relative"),
        ("src/../x.py", "save", 1, 2, 0, "file must not contain .."),
        ("./src/x.py", "save", 1, 2, 0, "file must not start with ./"),
        ("src/x.py", "", 1, 2, 0, "name must not be empty"),
        ("src/x.py", "sa\nve", 1, 2, 0, "name must not contain a newline"),
        ("src/x.py", "save", 0, 2, 0, "start_line must be positive"),
        ("src/x.py", "save", 3, 2, 0, "end_line must not precede start_line"),
        ("src/x.py", "save", 1, 2, -1, "score must not be negative"),
    ],
)
def test_cognitive_function_rejects_illegal_values(
    file: str,
    name: str,
    start: int,
    end: int,
    score: int,
    message: str,
) -> None:
    with pytest.raises(ValueError) as caught:
        CognitiveFunction(
            file=file,
            name=name,
            start_line=start,
            end_line=end,
            score=score,
            language="python",
        )

    assert str(caught.value) == message
