"""Application bootstrap helpers for Boardforge."""

from __future__ import annotations

from .backends import BackendRegistry
from .boards import BoardCatalog
from .engine import Engine
from .qemu import QemuBackend
from .renode import RenodeBackend


def create_default_registry() -> BackendRegistry:
    """Create a backend registry with the built-in backends."""

    registry = BackendRegistry()
    registry.register(QemuBackend())
    registry.register(RenodeBackend())
    return registry


def create_default_engine(boards: BoardCatalog | None = None) -> Engine:
    """Create an engine wired with the built-in backends and board catalog."""

    return Engine(create_default_registry(), boards=boards)
