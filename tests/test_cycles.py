"""Componentes fortemente conexos. Uma cadeia longa não pode estourar a recursão."""

from bob_quality.cycles import strongly_connected


def test_strongly_connected_handles_a_chain_longer_than_the_recursion_limit() -> None:
    count = 1100
    edges = {str(index): [str(index + 1)] for index in range(count - 1)}
    edges[str(count - 1)] = ["0"]

    components = strongly_connected(edges)

    assert len(components) == 1
    assert components[0] == frozenset(str(index) for index in range(count))
