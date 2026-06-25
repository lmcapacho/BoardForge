import pytest

from boardforge.backends import BackendRegistry


class DummyBackend:
    name = "dummy"

    def load(self, board, image_path) -> None:
        self.last_load = (board, image_path)

    def run(self) -> None:
        pass

    def pause(self) -> None:
        pass

    def stop(self) -> None:
        pass


def test_backend_registry_registers_and_resolves_backends() -> None:
    registry = BackendRegistry()
    backend = DummyBackend()

    registry.register(backend)

    assert registry.get("dummy") is backend
    assert registry.names() == ("dummy",)


def test_backend_registry_rejects_duplicate_names() -> None:
    registry = BackendRegistry()
    registry.register(DummyBackend())

    with pytest.raises(ValueError):
        registry.register(DummyBackend())
