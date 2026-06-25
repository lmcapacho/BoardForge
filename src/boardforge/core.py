"""Core domain models and backend contracts for Boardforge."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol


@dataclass(slots=True, frozen=True)
class MemoryRegion:
    """Describes a memory-mapped region exposed by a board."""

    name: str
    base: int
    size: int
    kind: str
    permissions: str = "rw"
    file: str | None = None


@dataclass(slots=True, frozen=True)
class Peripheral:
    """Describes a peripheral as seen by the engine."""

    name: str
    kind: str
    address: int | None = None
    size: int | None = None
    properties: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True, frozen=True)
class BoardSpec:
    """Backend-neutral board description."""

    name: str
    architecture: str
    cpu: str
    backend: str
    machine: str | None = None
    vendor: str | None = None
    description: str | None = None
    firmware_format: str = "elf"
    memory_regions: tuple[MemoryRegion, ...] = ()
    peripherals: tuple[Peripheral, ...] = ()
    backend_options: dict[str, Any] = field(default_factory=dict)
    source: Path | None = None


class Backend(Protocol):
    """Common execution contract for simulation backends."""

    name: str

    def load(self, board: BoardSpec, image_path: str | Path) -> None:
        """Load a board and firmware image into the backend."""

    def run(self) -> None:
        """Start or resume execution."""

    def pause(self) -> None:
        """Pause execution if the backend supports it."""

    def stop(self) -> None:
        """Stop execution and release backend resources."""
