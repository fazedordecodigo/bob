"""Componentes fortemente conexos. Uma cadeia longa não pode estourar a recursão."""

from bob_quality.cycles import strongly_connected


def test_strongly_connected_handles_a_chain_longer_than_the_recursion_limit() -> None:
    count = 1100
    edges = {str(index): [str(index + 1)] for index in range(count - 1)}
    edges[str(count - 1)] = ["0"]

    components = strongly_connected(edges)

    assert len(components) == 1
    assert components[0] == frozenset(str(index) for index in range(count))


def test_two_module_cycle_is_a_component_and_a_lone_module_is_not() -> None:
    assert strongly_connected({"a": ["b"], "b": ["a"], "solo": []}) == [frozenset({"a", "b"})]


def test_module_that_only_reaches_a_cycle_stays_out_of_it() -> None:
    assert strongly_connected({"a": ["b"], "b": ["c"], "c": ["b"]}) == [frozenset({"b", "c"})]


def test_module_that_only_appears_as_a_destination_is_a_node() -> None:
    assert strongly_connected({"a": ["b", "leaf"], "b": ["a"]}) == [frozenset({"a", "b"})]
    assert strongly_connected({"a": ["leaf"]}) == []


def test_two_separate_cycles_are_two_components() -> None:
    edges = {"a": ["b"], "b": ["a"], "c": ["d"], "d": ["c"], "e": ["a", "c"]}

    components = strongly_connected(edges)

    assert sorted(components, key=sorted) == [frozenset({"a", "b"}), frozenset({"c", "d"})]


def test_module_reached_twice_before_its_visit_still_closes_the_cycle() -> None:
    edges = {"a": ["b", "c"], "b": ["c"], "c": ["a"]}

    assert strongly_connected(edges) == [frozenset({"a", "b", "c"})]


def test_entry_module_pushed_twice_does_not_join_the_cycle_it_feeds() -> None:
    edges = {"a": ["d", "e"], "b": ["e"], "c": [], "d": ["b"], "e": ["b", "d"]}

    assert strongly_connected(edges) == [frozenset({"b", "d", "e"})]


def test_module_queued_twice_while_collecting_keeps_the_whole_component() -> None:
    edges = {
        "a": ["c", "d", "e"],
        "b": ["e"],
        "c": ["a"],
        "d": ["a", "b", "e"],
        "e": ["a", "d"],
    }

    assert strongly_connected(edges) == [frozenset({"a", "b", "c", "d", "e"})]
