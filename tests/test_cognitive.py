"""Veredito de complexidade cognitiva no núcleo."""

import importlib
import json
from pathlib import Path
from types import SimpleNamespace
from typing import get_args

import pytest

from bob_quality.check import _Measured, _assemble
from bob_quality.churn import ChurnUnavailable
from bob_quality.cognitive_gate import (
    _LanguageFunctions,
    _LanguageMiss,
    _MEASURE,
    _function_fields,
    _items,
    _measure_python,
    _measure_typescript,
    _parse_payload,
    _python_files,
    _python_functions,
    _relative,
    _run_eslint,
    _whole,
    run_cognitive_gate,
)
from bob_quality.config import SOURCE_LANGUAGES, Config
from bob_quality.core import cognitive_verdict
from bob_quality.messages import msg, render
from bob_quality.models import (
    Clone,
    CognitiveFunction,
    CognitiveLanguage,
    DepViolation,
    FunctionMetric,
    GateResult,
)
from bob_quality.mutate import MutationOutcome
from bob_quality.tools import ToolError


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


def test_score_below_the_limit_passes_with_the_gate_name() -> None:
    below = _function("under", score=14)
    diff = {"src/app.py": {1}}

    result, found, code = cognitive_verdict([below], 15, set(), diff)

    assert result.name == "cognitive"
    assert result.status == "passed"
    assert result.reason is None
    assert found == []
    assert code == 0


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
    row = {
        "file": "src/foo.ts",
        "name": "Foo::save",
        "start_line": 2,
        "end_line": 19,
        "score": 15,
    }
    with pytest.raises(ValueError) as messages_only:
        _parse_payload(json.dumps([{**row, "messages": []}]), tmp_path)
    assert str(messages_only.value) == "eslint payload is not domain json"
    with pytest.raises(ValueError) as path_only:
        _parse_payload(json.dumps([{**row, "filePath": "src/foo.ts"}]), tmp_path)
    assert str(path_only.value) == "eslint payload is not domain json"


def test_unreadable_payload_names_the_reason(tmp_path: Path) -> None:
    with pytest.raises(ValueError) as not_a_list:
        _parse_payload("{}", tmp_path)
    assert str(not_a_list.value) == "unreadable cognitive payload"
    with pytest.raises(ValueError) as not_a_row:
        _parse_payload("[1]", tmp_path)
    assert str(not_a_row.value) == "unreadable cognitive payload"
    with pytest.raises(ValueError) as blank_name:
        _parse_payload(
            json.dumps(
                [
                    {
                        "file": "src/foo.ts",
                        "name": "",
                        "start_line": 2,
                        "end_line": 19,
                        "score": 15,
                    }
                ]
            ),
            tmp_path,
        )
    assert str(blank_name.value) == "function is missing name"
    with pytest.raises(ValueError) as boolean_score:
        _parse_payload(
            json.dumps(
                [
                    {
                        "file": "src/foo.ts",
                        "name": "Foo::save",
                        "start_line": 2,
                        "end_line": 19,
                        "score": True,
                    }
                ]
            ),
            tmp_path,
        )
    assert str(boolean_score.value) == "function is missing score"


def test_relative_drops_a_leading_dot_slash(tmp_path: Path) -> None:
    assert _relative(tmp_path, "./src/foo.ts") == "src/foo.ts"


@pytest.mark.parametrize(
    ("file", "name", "start", "end", "score", "message"),
    [
        ("/abs.py", "save", 1, 2, 0, "file must be repo-relative"),
        ("src/../x.py", "save", 1, 2, 0, "file must not contain .."),
        ("./src/x.py", "save", 1, 2, 0, "file must not start with ./"),
        ("src/x.py", "", 1, 2, 0, "name must not be empty"),
        ("src/x.py", "sa\nve", 1, 2, 0, "name must not contain a newline"),
        ("src/x.py", "sa\rve", 1, 2, 0, "name must not contain a newline"),
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


def test_a_one_line_function_keeps_its_span() -> None:
    item = _function("save", score=0, start=4, end=4)

    assert (item.start_line, item.end_line) == (4, 4)


def test_no_configured_language_passes() -> None:
    result, found, code, versions = run_cognitive_gate(
        Path("."), SimpleNamespace(languages=()), {}
    )

    assert result == GateResult("cognitive", "passed")
    assert found == []
    assert code == 0
    assert versions == {}


def test_a_missing_tool_on_the_only_language_is_not_run(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setitem(_MEASURE, "python", _missing("complexipy"))

    result, found, code, versions = run_cognitive_gate(tmp_path, Config(), {})

    assert result == GateResult(
        "cognitive", "not_run", msg("cognitive.tool_missing", tool="complexipy")
    )
    assert found == []
    assert code == 0
    assert versions == {}


def test_two_misses_join_their_reasons(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setitem(_MEASURE, "python", _missing("complexipy"))
    monkeypatch.setitem(_MEASURE, "typescript", _missing("node"))

    result, found, code, versions = run_cognitive_gate(
        tmp_path, Config(languages=("python", "typescript")), {}
    )

    assert result == GateResult(
        "cognitive",
        "not_run",
        msg(
            "probe.joined",
            first=msg("cognitive.tool_missing", tool="complexipy"),
            second=msg("cognitive.tool_missing", tool="node"),
        ),
    )
    assert found == []
    assert code == 0
    assert versions == {}


def test_a_miss_still_warns_when_another_language_is_over(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    hot = _function("save", score=15, file="src/a.ts", language="typescript")

    def hit(cwd: Path, config: Config) -> _LanguageFunctions:
        return _LanguageFunctions([hot], {"eslint": "9.39.5"})

    monkeypatch.setitem(_MEASURE, "python", _missing("complexipy"))
    monkeypatch.setitem(_MEASURE, "typescript", hit)

    result, found, code, versions = run_cognitive_gate(
        tmp_path,
        Config(languages=("python", "typescript")),
        {"src/a.ts": {1}},
    )

    assert result.name == "cognitive"
    assert result.status == "warn"
    assert code == 0
    assert found == [hot]
    assert versions == {"eslint": "9.39.5"}


def test_missing_complexipy_names_the_tool(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def missing() -> object:
        raise ImportError("missing")

    monkeypatch.setattr("bob_quality.cognitive_gate._load_complexipy", missing)

    outcome = _measure_python(tmp_path, Config())

    assert isinstance(outcome, _LanguageMiss)
    assert outcome.reason == msg("cognitive.tool_missing", tool="complexipy")


def test_a_broken_measurer_names_the_tool_and_the_detail(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "src"
    source.mkdir()
    (source / "a.py").write_text("x = 1\n")

    def broken(path: str, **kwargs: object) -> object:
        raise RuntimeError("boom {x}\nsecond")

    def blank(path: str, **kwargs: object) -> object:
        raise RuntimeError("   ")

    monkeypatch.setattr("bob_quality.cognitive_gate._load_complexipy", _module(broken))
    outcome = _measure_python(tmp_path, Config())
    assert isinstance(outcome, _LanguageMiss)
    assert outcome.reason == msg("cognitive.tool_bad", tool="complexipy", detail="boom (x)")

    monkeypatch.setattr("bob_quality.cognitive_gate._load_complexipy", _module(blank))
    outcome = _measure_python(tmp_path, Config())
    assert isinstance(outcome, _LanguageMiss)
    assert outcome.reason == msg("cognitive.tool_bad", tool="complexipy", detail="failed")


def test_python_files_keep_a_py_file_and_skip_the_rest(tmp_path: Path) -> None:
    (tmp_path / "single.py").write_text("x = 1\n")
    (tmp_path / "notes.txt").write_text("x\n")
    (tmp_path / "pkg" / "a_skip").mkdir(parents=True)
    (tmp_path / "pkg" / "a_skip" / "hidden.py").write_text("x = 1\n")
    (tmp_path / "pkg" / "z.py").write_text("x = 1\n")
    (tmp_path / "other").mkdir()
    (tmp_path / "other" / "a.py").write_text("x = 1\n")
    config = Config(
        include=("single.py", "notes.txt", "pkg", "missing", "other"),
        exclude=("a_skip",),
    )

    found = [path.relative_to(tmp_path).as_posix() for path in _python_files(tmp_path, config)]

    assert found == ["single.py", "pkg/z.py", "other/a.py"]


def test_python_functions_keep_an_ignored_function_and_skip_the_module(tmp_path: Path) -> None:
    source = tmp_path / "src"
    source.mkdir()
    (source / "sample.py").write_text(
        "def kept(n):\n"
        "    if n:\n"
        "        return 1\n"
        "    return 0\n"
        "\n"
        "def ignored(n):  # complexipy: ignore\n"
        "    if n:\n"
        "        return 1\n"
        "    return 0\n"
        "\n"
        "if True:\n"
        "    value = 1\n"
    )

    found = _python_functions(
        tmp_path, Config(include=("src",)), importlib.import_module("complexipy")
    )

    assert [(item.name, item.language, item.file) for item in found] == [
        ("kept", "python", "src/sample.py"),
        ("ignored", "python", "src/sample.py"),
    ]


def test_function_fields_read_a_complexipy_row_and_reject_a_broken_one() -> None:
    assert _function_fields(
        SimpleNamespace(name="save", complexity=3, line_start=2, line_end=4)
    ) == ("save", 3, 2, 4)
    message = "function is missing name, complexity, line_start, or line_end"
    broken = [
        SimpleNamespace(complexity=1, line_start=1, line_end=2),
        SimpleNamespace(name="", complexity=1, line_start=1, line_end=2),
        SimpleNamespace(name=1, complexity=1, line_start=1, line_end=2),
        SimpleNamespace(name="save", complexity=True, line_start=1, line_end=2),
        SimpleNamespace(name="save", complexity=1, line_start=True, line_end=2),
        SimpleNamespace(name="save", complexity=1, line_start=1, line_end=True),
        SimpleNamespace(name="save", complexity="x", line_start=1, line_end=2),
    ]
    for item in broken:
        with pytest.raises(ValueError) as caught:
            _function_fields(item)
        assert str(caught.value) == message
    missing_attribute = [
        SimpleNamespace(name="save", line_start=1, line_end=2),
        SimpleNamespace(name="save", complexity=1, line_end=2),
        SimpleNamespace(name="save", complexity=1, line_start=1),
    ]
    for item in missing_attribute:
        with pytest.raises(ValueError) as caught:
            _function_fields(item)
        assert str(caught.value) == message


def test_python_functions_rejects_a_result_without_functions(tmp_path: Path) -> None:
    source = tmp_path / "src"
    source.mkdir()
    (source / "a.py").write_text("x = 1\n")

    def measure(path: str, **kwargs: object) -> object:
        return SimpleNamespace()

    with pytest.raises(ValueError) as caught:
        _python_functions(
            tmp_path,
            Config(include=("src",)),
            SimpleNamespace(file_complexity=measure),
        )

    assert str(caught.value) == "function is missing name, complexity, line_start, or line_end"


def test_whole_rejects_a_bool_and_items_copy_a_non_list() -> None:
    assert _whole(1) is True
    assert _whole(True) is False
    assert _whole(1.0) is False
    assert _items([1]) == [1]
    assert _items((1, 2)) == [1, 2]
    with pytest.raises(ValueError) as caught:
        _items(None)
    assert str(caught.value) == "function is missing name, complexity, line_start, or line_end"


def _missing(tool: str):
    def miss(cwd: Path, config: Config) -> _LanguageMiss:
        return _LanguageMiss(msg("cognitive.tool_missing", tool=tool))

    return miss


def _module(measure):
    def load() -> object:
        return SimpleNamespace(__name__="complexipy", file_complexity=measure)

    return load


def test_assemble_keeps_a_cloned_file_in_the_diff_and_the_mutation_summary() -> None:
    clone = Clone(
        first_file="src/a.py",
        first_start=1,
        first_end=2,
        second_file="src/b.py",
        second_start=1,
        second_end=2,
        lines=2,
        tokens=10,
    )
    summary = {"remutated": ["src/a.py:save"]}
    waivers = [{"id": "cognitive:src/a.py:save"}]
    survivors = [{"file": "src/a.py", "waiver": "kept"}]
    cognitive = [_function("save", score=15)]
    changed = FunctionMetric(
        lang="python",
        module="a",
        name="save",
        file="src/a.py",
        start_line=1,
        end_line=2,
        cc=4,
        coverage=0.0,
        crap=20.0,
        changed=True,
    )
    debt = FunctionMetric(
        lang="python",
        module="b",
        name="legacy",
        file="src/b.py",
        start_line=1,
        end_line=2,
        cc=4,
        coverage=0.0,
        crap=20.0,
        changed=False,
    )
    blocking = DepViolation("src.a", "src.b", "no-cycles", True)
    parked = DepViolation("src.c", "src.d", "no-cycles", False)
    measured = _Measured(
        clones=[clone],
        metrics=[changed, debt],
        violations=[blocking, parked],
        cognitive=cognitive,
        mutation=MutationOutcome(
            result=GateResult("mutate", "passed"),
            exit_code=0,
            versions={},
            waivers=waivers,
            survivors=survivors,
            summary=summary,
        ),
    )

    report = _assemble(
        measured, "abc", "main", {"src/a.py": {1}}, 10.0, "bob check", ChurnUnavailable()
    )

    assert report.schema_version == 1
    assert report.commit == "abc"
    assert report.base == "main"
    assert report.generated_at.endswith("+00:00")
    assert report.reproduce == "bob check"
    assert report.clones == [clone]
    assert report.focus == [{"file": "src/a.py", "risk": 20.0, "clone": True}]
    assert report.mutation == summary
    assert report.waivers == waivers
    assert report.survivors == survivors
    assert report.cognitive == cognitive
    assert report.top_crap[0]["name"] == "save"
    assert report.old_debt[0]["name"] == "legacy"
    assert report.dependencies == [
        {"origin": "src.a", "destination": "src.b", "rule": "no-cycles"}
    ]
    assert report.old_dependencies == [
        {"origin": "src.c", "destination": "src.d", "rule": "no-cycles"}
    ]

    loaded = [{"id": "cognitive:src/b.py:legacy"}]
    idle = _assemble(
        _Measured(loaded_waivers=loaded),
        "abc",
        "main",
        {},
        10.0,
        "bob check",
        ChurnUnavailable(),
    )
    assert idle.commit == "abc"
    assert idle.base == "main"
    assert idle.reproduce == "bob check"
    assert idle.clones == []
    assert idle.survivors == []
    assert idle.mutation is None
    assert idle.waivers == loaded


def test_measure_typescript_misses_when_node_is_absent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def prefix() -> Path:
        raise AssertionError("npm prefix is not used when node is missing")

    monkeypatch.setattr("bob_quality.cognitive_gate.node_missing_message", lambda: msg("x"))
    monkeypatch.setattr("bob_quality.cognitive_gate.npm_prefix", prefix)

    outcome = _measure_typescript(tmp_path, Config())

    assert isinstance(outcome, _LanguageMiss)
    assert outcome.reason == msg("cognitive.tool_missing", tool="node")


def test_measure_typescript_misses_when_the_npm_prefix_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def prefix() -> Path:
        raise ToolError("missing")

    monkeypatch.setattr("bob_quality.cognitive_gate.node_missing_message", lambda: None)
    monkeypatch.setattr("bob_quality.cognitive_gate.npm_prefix", prefix)

    outcome = _measure_typescript(tmp_path, Config())

    assert isinstance(outcome, _LanguageMiss)
    assert outcome.reason == msg("cognitive.tool_missing", tool="eslint")


def test_measure_typescript_returns_the_functions_and_the_versions(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    prefix = tmp_path / "prefix"
    row = {
        "file": "src/foo.ts",
        "name": "Foo::save",
        "start_line": 2,
        "end_line": 4,
        "score": 15,
    }

    def version(got: Path, package: str) -> str:
        assert got == prefix
        return {"eslint": "9.39.5", "eslint-plugin-sonarjs": "2.0.4"}[package]

    def eslint(cwd: Path, config: Config, got: Path) -> str:
        assert cwd == tmp_path
        assert got == prefix
        assert config.max_cognitive == 15
        return json.dumps([row])

    monkeypatch.setattr("bob_quality.cognitive_gate.node_missing_message", lambda: None)
    monkeypatch.setattr("bob_quality.cognitive_gate.npm_prefix", lambda: prefix)
    monkeypatch.setattr("bob_quality.cognitive_gate.installed_npm_version", version)
    monkeypatch.setattr("bob_quality.cognitive_gate._run_eslint", eslint)

    outcome = _measure_typescript(tmp_path, Config(max_cognitive=15))

    assert isinstance(outcome, _LanguageFunctions)
    assert outcome.versions == {"eslint": "9.39.5", "eslint-plugin-sonarjs": "2.0.4"}
    assert outcome.functions == [
        CognitiveFunction(
            file="src/foo.ts",
            name="Foo::save",
            start_line=2,
            end_line=4,
            score=15,
            language="typescript",
        )
    ]


def test_measure_typescript_wraps_a_bad_eslint(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def broken(cwd: Path, config: Config, prefix: Path) -> str:
        raise OSError("disk {full}\nsecond")

    monkeypatch.setattr("bob_quality.cognitive_gate.node_missing_message", lambda: None)
    monkeypatch.setattr("bob_quality.cognitive_gate.npm_prefix", lambda: tmp_path)
    monkeypatch.setattr(
        "bob_quality.cognitive_gate.installed_npm_version",
        lambda prefix, package: "1",
    )
    monkeypatch.setattr("bob_quality.cognitive_gate._run_eslint", broken)

    outcome = _measure_typescript(tmp_path, Config())

    assert isinstance(outcome, _LanguageMiss)
    assert outcome.reason == msg("cognitive.tool_bad", tool="eslint", detail="disk (full)")


def test_measure_typescript_wraps_a_value_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def broken(cwd: Path, config: Config, prefix: Path) -> str:
        raise ValueError("eslint failed")

    monkeypatch.setattr("bob_quality.cognitive_gate.node_missing_message", lambda: None)
    monkeypatch.setattr("bob_quality.cognitive_gate.npm_prefix", lambda: tmp_path)
    monkeypatch.setattr(
        "bob_quality.cognitive_gate.installed_npm_version",
        lambda prefix, package: "1",
    )
    monkeypatch.setattr("bob_quality.cognitive_gate._run_eslint", broken)

    outcome = _measure_typescript(tmp_path, Config())

    assert isinstance(outcome, _LanguageMiss)
    assert outcome.reason == msg("cognitive.tool_bad", tool="eslint", detail="eslint failed")


def test_run_eslint_sends_the_payload_and_returns_stdout(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    prefix = tmp_path / "prefix"
    seen: dict[str, object] = {}

    def fake_run(args: list[str], **kwargs: object) -> SimpleNamespace:
        seen["args"] = args
        seen["kwargs"] = kwargs
        return SimpleNamespace(returncode=0, stdout="[]\n", stderr="noise")

    monkeypatch.setenv("PYTEST_SENTINEL", "1")
    monkeypatch.setenv("BOB_KEEP", "yes")
    monkeypatch.setattr("bob_quality.cognitive_gate.subprocess.run", fake_run)
    config = Config(include=("src",), exclude=("dist",), max_cognitive=15)

    raw = _run_eslint(tmp_path, config, prefix)

    script = (
        Path(__file__).resolve().parents[1]
        / "src"
        / "bob_quality"
        / "js"
        / "eslint_cognitive.mjs"
    )
    kwargs = seen["kwargs"]
    assert isinstance(kwargs, dict)
    env = kwargs["env"]
    assert isinstance(env, dict)
    assert raw == "[]\n"
    assert seen["args"] == ["node", str(script)]
    assert kwargs["cwd"] == tmp_path
    assert kwargs["capture_output"] is True
    assert kwargs["text"] is True
    assert json.loads(str(kwargs["input"])) == {
        "limit": 15,
        "cwd": str(tmp_path.resolve()),
        "include": ["src"],
        "exclude": ["dist"],
    }
    assert "PYTEST_SENTINEL" not in env
    assert "PYTEST_CURRENT_TEST" not in env
    assert env["BOB_KEEP"] == "yes"
    assert env["NODE_PATH"] == str(prefix / "node_modules")


def test_run_eslint_prefers_stderr_and_strips_it(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fake_run(args: list[str], **kwargs: object) -> SimpleNamespace:
        return SimpleNamespace(returncode=2, stdout="out\n", stderr="  boom  \n")

    monkeypatch.setattr("bob_quality.cognitive_gate.subprocess.run", fake_run)

    with pytest.raises(ValueError) as caught:
        _run_eslint(tmp_path, Config(), tmp_path)

    assert str(caught.value) == "boom"


def test_run_eslint_uses_stdout_when_stderr_is_empty(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fake_run(args: list[str], **kwargs: object) -> SimpleNamespace:
        return SimpleNamespace(returncode=-1, stdout="  from stdout  ", stderr="")

    monkeypatch.setattr("bob_quality.cognitive_gate.subprocess.run", fake_run)

    with pytest.raises(ValueError) as caught:
        _run_eslint(tmp_path, Config(), tmp_path)

    assert str(caught.value) == "from stdout"


def test_run_eslint_names_a_blank_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fake_run(args: list[str], **kwargs: object) -> SimpleNamespace:
        return SimpleNamespace(returncode=1, stdout="   ", stderr="")

    monkeypatch.setattr("bob_quality.cognitive_gate.subprocess.run", fake_run)

    with pytest.raises(ValueError) as caught:
        _run_eslint(tmp_path, Config(), tmp_path)

    assert str(caught.value) == "eslint failed"
