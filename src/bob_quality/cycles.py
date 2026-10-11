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
    seen.add(node)
    for nxt in edges.get(node, ()):
        _walk(nxt, edges, seen, order)
    order.append(node)


def _inbound(nodes: set[str], edges: dict[str, list[str]]) -> dict[str, list[str]]:
    inbound = {node: [] for node in nodes}
    for origin, destinations in edges.items():
        _link(inbound, origin, destinations)
    return inbound


def _link(inbound: dict[str, list[str]], origin: str, destinations: list[str]) -> None:
    for destination in destinations:
        if destination in inbound and origin in inbound:
            inbound[destination].append(origin)


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
    seen.add(node)
    component.add(node)
    for nxt in inbound.get(node, ()):
        _collect(nxt, inbound, seen, component)
