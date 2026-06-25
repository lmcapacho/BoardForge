from pathlib import Path

import pytest

from boardforge.boards import BoardValidationError, load_board_spec


def test_load_board_spec_parses_sample_board() -> None:
    board = load_board_spec(Path("boards/qemu-virt-rv32.yaml"))

    assert board.name == "qemu-virt-rv32"
    assert board.backend == "qemu"
    assert board.machine == "virt"
    assert len(board.memory_regions) == 2
    assert board.memory_regions[0].base == 0x20000000
    assert board.peripherals[0].kind == "uart"


def test_load_board_spec_requires_core_fields(tmp_path: Path) -> None:
    board_file = tmp_path / "invalid-board.yaml"
    board_file.write_text("name: invalid\nbackend: qemu\n", encoding="utf-8")

    with pytest.raises(BoardValidationError):
        load_board_spec(board_file)
