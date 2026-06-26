from pathlib import Path

import pytest

from boardforge.boards import BoardCatalog, board_from_mapping
from boardforge.qemu import QemuBackend, QemuBackendError


@pytest.fixture
def qemu_image(tmp_path: Path) -> Path:
    image = tmp_path / "firmware.elf"
    image.write_bytes(b"ELF")
    return image


def test_qemu_backend_prepares_builtin_board_session(qemu_image: Path) -> None:
    board = BoardCatalog.default().get("qemu-virt-rv32")
    backend = QemuBackend()

    backend.load(board, qemu_image)

    assert backend.session is not None
    assert backend.session.image_path == qemu_image
    assert backend.session.command[:4] == (
        "qemu-system-riscv32",
        "-nographic",
        "-machine",
        "virt",
    )
    assert "-cpu" in backend.session.command
    assert "rv32" in backend.session.command
    assert "-kernel" in backend.session.command
    assert "-S" not in backend.session.command
    assert "-s" not in backend.session.command


def test_qemu_backend_rejects_wrong_backend(qemu_image: Path) -> None:
    board = board_from_mapping(
        {
            "name": "wrong-backend",
            "architecture": "riscv32",
            "cpu": "rv32imac",
            "backend": "renode",
            "machine": "virt",
        }
    )

    backend = QemuBackend()

    with pytest.raises(QemuBackendError):
        backend.load(board, qemu_image)


def test_qemu_backend_requires_machine_name(qemu_image: Path) -> None:
    board = board_from_mapping(
        {
            "name": "invalid-qemu",
            "architecture": "riscv32",
            "cpu": "rv32imac",
            "backend": "qemu",
        }
    )

    backend = QemuBackend()

    with pytest.raises(QemuBackendError):
        backend.load(board, qemu_image)


def test_qemu_backend_rejects_invalid_args_type(qemu_image: Path) -> None:
    board = board_from_mapping(
        {
            "name": "invalid-args",
            "architecture": "riscv32",
            "cpu": "rv32imac",
            "backend": "qemu",
            "machine": "virt",
            "backend_options": {"args": {"bad": True}},
        }
    )

    backend = QemuBackend()

    with pytest.raises(QemuBackendError):
        backend.load(board, qemu_image)


def test_qemu_backend_defaults_cpu_model_from_architecture(qemu_image: Path) -> None:
    board = board_from_mapping(
        {
            "name": "default-cpu-model",
            "architecture": "riscv32",
            "cpu": "rv32i",
            "backend": "qemu",
            "machine": "virt",
        }
    )

    backend = QemuBackend()
    backend.load(board, qemu_image)

    assert backend.session is not None
    assert "rv32" in backend.session.command
