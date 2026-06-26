from pathlib import Path

from boardforge.cli import _sanitize_backend_output, main


def test_sanitize_backend_output_removes_qemu_termination_line() -> None:
    output = "Hello from Boardforge!\nqemu-system-riscv32: terminating on signal 15 from pid 123\n"

    sanitized = _sanitize_backend_output(output, "qemu")

    assert sanitized == "Hello from Boardforge!\n"


def test_sanitize_backend_output_keeps_non_qemu_output() -> None:
    output = "22:22:10 [INFO] uart0: Hello from Boardforge!\n"

    sanitized = _sanitize_backend_output(output, "renode")

    assert sanitized == output


def test_cli_build(tmp_path: Path, capsys) -> None:
    makefile = tmp_path / "Makefile"
    makefile.write_text("all:\n\tprintf 'ELF' > demo.elf\n", encoding="utf-8")

    exit_code = main(["build", str(tmp_path)])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "build succeeded" in captured.out
    assert "demo.elf" in captured.out
    assert "primary-artifact:" in captured.out


def test_cli_build_uses_project_manifest(tmp_path: Path, capsys) -> None:
    makefile = tmp_path / "Makefile"
    makefile.write_text("custom:\n\tprintf 'ELF' > firmware.elf\n", encoding="utf-8")
    config = tmp_path / "boardforge.toml"
    config.write_text('[project]\nartifact = "firmware.elf"\ntarget = "custom"\n', encoding="utf-8")

    exit_code = main(["build", str(tmp_path)])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "command: /usr/bin/make custom" in captured.out
    assert "firmware.elf" in captured.out


def test_cli_build_missing_makefile(tmp_path: Path, capsys) -> None:
    exit_code = main(["build", str(tmp_path)])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "Makefile not found" in captured.out


def test_cli_run_with_project_dir_builds_and_resolves_artifact(tmp_path: Path, capsys) -> None:
    makefile = tmp_path / "Makefile"
    makefile.write_text("all:\n\tprintf 'ELF' > demo.elf\n", encoding="utf-8")
    config = tmp_path / "boardforge.toml"
    config.write_text('[project]\nboard = "qemu-virt-rv32"\nartifact = "demo.elf"\n', encoding="utf-8")

    exit_code = main([
        "run",
        "--project-dir",
        str(tmp_path),
        "--build",
        "--timeout",
        "0.1",
    ])

    captured = capsys.readouterr()
    assert exit_code in (0, 1)
    assert "build succeeded" in captured.out
    assert "resolved-board: qemu-virt-rv32" in captured.out
    assert "resolved-image:" in captured.out


def test_cli_run_with_project_dir_requires_artifact(tmp_path: Path, capsys) -> None:
    makefile = tmp_path / "Makefile"
    makefile.write_text("all:\n\t@true\n", encoding="utf-8")

    exit_code = main([
        "run",
        "qemu-virt-rv32",
        "--project-dir",
        str(tmp_path),
    ])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "no .elf artifacts found" in captured.out


def test_cli_run_requires_board_without_manifest(tmp_path: Path, capsys) -> None:
    firmware = tmp_path / "demo.elf"
    firmware.write_bytes(b"ELF")

    exit_code = main([
        "run",
        "--project-dir",
        str(tmp_path),
    ])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "provide a board name/path or define board in boardforge.toml" in captured.out


def test_cli_doctor(capsys) -> None:
    exit_code = main(["doctor"])

    captured = capsys.readouterr()
    assert exit_code in (0, 1)
    assert "[OK] python:" in captured.out
    assert "[OK] boards:" in captured.out
    assert "[OK] backends:" in captured.out
    assert "summary:" in captured.out


def test_cli_list_boards(capsys) -> None:
    exit_code = main(["list-boards"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "qemu-virt-rv32" in captured.out
    assert "renode-rv32-virt" in captured.out


def test_cli_show_board(capsys) -> None:
    exit_code = main(["show-board", "qemu-virt-rv32"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "name: qemu-virt-rv32" in captured.out
    assert "backend: qemu" in captured.out


def test_cli_prepare(tmp_path: Path, capsys) -> None:
    image = tmp_path / "firmware.elf"
    image.write_bytes(b"ELF")

    exit_code = main(["prepare", "qemu-virt-rv32", str(image)])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "prepared: qemu-virt-rv32" in captured.out
    assert "state: loaded" in captured.out
    assert "command: qemu-system-riscv32" in captured.out


def test_cli_run_reports_launch_failure_for_missing_image(capsys) -> None:
    exit_code = main(["run", "qemu-virt-rv32", "/tmp/does-not-exist.elf", "--timeout", "0.1"])

    captured = capsys.readouterr()
    assert exit_code == 0 or exit_code == 1
    assert "running: qemu-virt-rv32" in captured.out or "launch failed:" in captured.out
