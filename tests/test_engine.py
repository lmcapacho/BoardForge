from pathlib import Path

import pytest

from boardforge.backends import BackendRegistry
from boardforge.engine import Engine, EngineState


class DummyBackend:
    name = "qemu"

    def __init__(self) -> None:
        self.events: list[tuple[str, object]] = []

    def load(self, board, image_path) -> None:
        self.events.append(("load", board.name, Path(image_path)))

    def run(self) -> None:
        self.events.append(("run",))

    def pause(self) -> None:
        self.events.append(("pause",))

    def stop(self) -> None:
        self.events.append(("stop",))


def make_engine() -> tuple[Engine, DummyBackend]:
    registry = BackendRegistry()
    backend = DummyBackend()
    registry.register(backend)
    return Engine(registry), backend


def test_engine_loads_board_from_file_and_tracks_session() -> None:
    engine, backend = make_engine()

    session = engine.load("boards/qemu-virt-rv32.yaml", "firmware/demo.elf")

    assert session.board.name == "qemu-virt-rv32"
    assert session.backend_name == "qemu"
    assert engine.state is EngineState.LOADED
    assert backend.events == [("load", "qemu-virt-rv32", Path("firmware/demo.elf"))]


def test_engine_loads_board_from_catalog_name() -> None:
    engine, backend = make_engine()

    session = engine.load("qemu-virt-rv32", "firmware/demo.elf")

    assert session.board.machine == "virt"
    assert engine.state is EngineState.LOADED
    assert backend.events == [("load", "qemu-virt-rv32", Path("firmware/demo.elf"))]


def test_engine_runs_pauses_and_stops_loaded_session() -> None:
    engine, backend = make_engine()
    engine.load("boards/qemu-virt-rv32.yaml", "firmware/demo.elf")

    engine.run()
    engine.pause()
    engine.stop()

    assert engine.state is EngineState.IDLE
    assert engine.session is None
    assert backend.events == [
        ("load", "qemu-virt-rv32", Path("firmware/demo.elf")),
        ("run",),
        ("pause",),
        ("stop",),
    ]


def test_engine_rejects_invalid_state_transitions() -> None:
    engine, _ = make_engine()

    with pytest.raises(RuntimeError):
        engine.run()

    engine.load("boards/qemu-virt-rv32.yaml", "firmware/demo.elf")

    with pytest.raises(RuntimeError):
        engine.pause()
