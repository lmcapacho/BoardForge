from boardforge.boards import BoardCatalog
from boardforge.renode import RenodeBackend


def test_catalog_lists_builtin_qemu_and_renode_boards() -> None:
    names = BoardCatalog.default().names()

    assert "qemu-virt-rv32" in names
    assert "renode-rv32-virt" in names


def test_builtin_renode_board_resolves_relative_platform_path(tmp_path) -> None:
    catalog = BoardCatalog.default()
    board = catalog.get("renode-rv32-virt")
    image = tmp_path / "firmware.elf"
    image.write_bytes(b"ELF")

    backend = RenodeBackend()
    backend.load(board, image)

    assert backend.session is not None
    assert backend.session.platform_path.name == "renode-rv32-virt.repl"
    assert backend.session.platform_path.parent.name == "platforms"
    assert any("showAnalyzer sysbus.uart0" == command for command in board.backend_options["monitor_commands"])
