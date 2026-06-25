"""Backend registry primitives."""

from __future__ import annotations

from typing import Iterable

from .core import Backend


class BackendRegistry:
    """Maps backend names to backend instances."""

    def __init__(self) -> None:
        self._backends: dict[str, Backend] = {}

    def register(self, backend: Backend) -> None:
        if backend.name in self._backends:
            raise ValueError(f"backend '{backend.name}' is already registered")
        self._backends[backend.name] = backend

    def get(self, name: str) -> Backend:
        try:
            return self._backends[name]
        except KeyError as exc:
            raise KeyError(f"backend '{name}' is not registered") from exc

    def names(self) -> tuple[str, ...]:
        return tuple(sorted(self._backends))

    def items(self) -> Iterable[tuple[str, Backend]]:
        return self._backends.items()
