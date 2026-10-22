"""Guarda de rede dos testes (U5-N16): ativa só com BOB_NET_GUARD_LOG."""

import os
import socket

_LOG = os.environ.get("BOB_NET_GUARD_LOG")
if _LOG:
    _CONNECT = socket.socket.connect
    _CONNECT_EX = socket.socket.connect_ex

    def _deny(name: str, argument: object) -> None:
        with open(_LOG, "a") as handle:
            handle.write(f"{name} {argument!r}\n")
        raise OSError("bob net guard: rede bloqueada nos testes")

    def _connect(self: socket.socket, address: object) -> object:
        if self.family in (socket.AF_INET, socket.AF_INET6):
            _deny("connect", address)
        return _CONNECT(self, address)

    def _connect_ex(self: socket.socket, address: object) -> object:
        if self.family in (socket.AF_INET, socket.AF_INET6):
            _deny("connect_ex", address)
        return _CONNECT_EX(self, address)

    def _getaddrinfo(*args: object, **_kwargs: object) -> object:
        _deny("getaddrinfo", args)

    socket.socket.connect = _connect  # type: ignore[method-assign]
    socket.socket.connect_ex = _connect_ex  # type: ignore[method-assign]
    socket.getaddrinfo = _getaddrinfo  # type: ignore[assignment]
