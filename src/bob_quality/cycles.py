"""Componentes fortemente conexos de um grafo de importação (arestas do grimp)."""

from __future__ import annotations


def strongly_connected(edges: dict[str, list[str]]) -> list[frozenset[str]]:
    """Devolve só os componentes com mais de um módulo."""
    nodes = set(edges)
    for destinations in edges.values():
        nodes.update(destinations)
    order = _postorder(nodes, edges)
    inbound = _inbound(nodes, edges)
    return [component for component in _assign(order, inbound) if len(component) > 1]


def _postorder(nodes: set[str], edges: dict[str, list[str]]) -> list[str]:
    seen: set[str] = set()
    order: list[str] = []
    for node in sorted(nodes):
        _walk(node, edges, seen, order)
    return order


def _walk(
    node: str,
    edges: dict[str, list[str]],
    seen: set[str],
    order: list[str],
) -> None:
    if node in seen:
        return
    stack: list[tuple[str, bool]] = [(node, False)]
    while stack:
        current, expanded = stack.pop()
        if expanded:
            order.append(current)
            continue
        if current in seen:
            continue
        seen.add(current)
        stack.append((current, True))
        for nxt in reversed(tuple(edges.get(current, ()))):
            if nxt not in seen:
                stack.append((nxt, False))


def _inbound(nodes: set[str], edges: dict[str, list[str]]) -> dict[str, list[str]]:
    inbound: dict[str, list[str]] = {node: [] for node in nodes}
    for origin, destinations in edges.items():
        for destination in destinations:
            inbound[destination].append(origin)
    return inbound


def _assign(order: list[str], inbound: dict[str, list[str]]) -> list[frozenset[str]]:
    seen: set[str] = set()
    components: list[frozenset[str]] = []
    for node in reversed(order):
        if node in seen:
            continue
        component: set[str] = set()
        _collect(node, inbound, seen, component)
        components.append(frozenset(component))
    return components


def _collect(
    node: str,
    inbound: dict[str, list[str]],
    seen: set[str],
    component: set[str],
) -> None:
    if node in seen:
        return
    stack = [node]
    while stack:
        current = stack.pop()
        if current in seen:
            continue
        seen.add(current)
        component.add(current)
        for nxt in inbound[current]:
            if nxt not in seen:
                stack.append(nxt)
