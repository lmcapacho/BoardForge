from pathlib import Path

import pytest

from boardforge.boards import board_from_mapping
from boardforge.renode import RenodeBackend, RenodeBackendError


@pytest.fixture
def renode_assets(tmp_path: Path) -> tuple[Path, Path]:
    platform = tmp_path / "platform.repl"
    platform.write_text("cpu: CPU.RiscV32 @ sysbus\n", encoding="utf-8")
    image = tmp_path / "firmware.elf"
    image.write_bytes(b"ELF")
    return platform, image


def test_renode_backend_prepares_launch_session(renode_assets: tuple[Path, Path]) -> None:
    platform, image = renode_assets
    board = board_from_mapping(
        {
            "name": "demo-renode",
            "architecture": "riscv32",
            "cpu": "rv32imac",
            "backend": "renode",
            "backend_options": {
                "platform": str(platform),
                "args": ["--disable-xwt"],
                "monitor_commands": ["start"],
            },
        }
    )

    backend = RenodeBackend()
    backend.load(board, image)

    assert backend.session is not None
    assert backend.session.platform_path == platform
    assert backend.session.image_path == image
    assert backend.session.command[1:5] == ('--console', '--disable-xwt', '--port', '-1')
    assert backend.session.command[-1] == str(backend.session.script_path)
    assert "start" in backend.session.script_path.read_text(encoding="utf-8")


def test_renode_backend_rejects_missing_platform(renode_assets: tuple[Path, Path]) -> None:
    _, image = renode_assets
    board = board_from_mapping(
        {
            "name": "invalid-renode",
            "architecture": "riscv32",
            "cpu": "rv32imac",
            "backend": "renode",
        }
    )

    backend = RenodeBackend()

    with pytest.raises(RenodeBackendError):
        backend.load(board, image)


def test_renode_backend_rejects_wrong_backend(renode_assets: tuple[Path, Path]) -> None:
    platform, image = renode_assets
    board = board_from_mapping(
        {
            "name": "wrong-backend",
            "architecture": "riscv32",
            "cpu": "rv32imac",
            "backend": "qemu",
            "backend_options": {"platform": str(platform)},
        }
    )

    backend = RenodeBackend()

    with pytest.raises(RenodeBackendError):
        backend.load(board, image)


def test_renode_backend_resolves_relative_platform_paths(tmp_path: Path) -> None:
    boards_dir = tmp_path / "boards"
    boards_dir.mkdir()
    platform = boards_dir / "relative-platform.repl"
    platform.write_text("cpu: CPU.RiscV32 @ sysbus\n", encoding="utf-8")
    board_file = boards_dir / "board.yaml"
    board_file.write_text("name: placeholder\n", encoding="utf-8")
    image = tmp_path / "firmware.elf"
    image.write_bytes(b"ELF")

    board = board_from_mapping(
        {
            "name": "relative-renode",
            "architecture": "riscv32",
            "cpu": "rv32imac",
            "backend": "renode",
            "backend_options": {"platform": "relative-platform.repl"},
        },
        source=board_file,
    )

    backend = RenodeBackend()
    backend.load(board, image)

    assert backend.session is not None
    assert backend.session.platform_path == platform.resolve()
