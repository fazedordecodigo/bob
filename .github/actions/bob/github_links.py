"""Leitura do cabeçalho Link da API do GitHub."""

from __future__ import annotations


def next_link(header: str) -> str | None:
    for part in header.split(","):
        if 'rel="next"' not in part:
            continue
        start = part.find("<")
        end = part.find(">")
        if start != -1 and end != -1:
            return part[start + 1 : end]
    return None
