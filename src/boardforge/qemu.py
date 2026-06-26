"""QEMU backend adapter."""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from .core import BoardSpec


class QemuBackendError(RuntimeError):
    """Raised when the QEMU backend cannot prepare or control a session."""


@dataclass(slots=True)
class QemuSession:
    """Prepared QEMU launch data for a board execution session."""

    board: BoardSpec
    image_path: Path
    command: tuple[str, ...]
    process: subprocess.Popen[str] | None = None


class QemuBackend:
    """Minimal QEMU backend that prepares a launchable session."""

    name = "qemu"

    def __init__(self, binary: str = "qemu-system-riscv32", extra_args: Sequence[str] | None = None) -> None:
        self.binary = binary
        self.extra_args = tuple(extra_args) if extra_args is not None else ("-nographic",)
        self.session: QemuSession | None = None

    def load(self, board: BoardSpec, image_path: str | Path) -> None:
        if board.backend != self.name:
            raise QemuBackendError(
                f"board '{board.name}' targets backend '{board.backend}', not '{self.name}'"
            )

        if not board.machine:
            raise QemuBackendError("qemu boards must define a machine name")

        resolved_image = Path(image_path).resolve()
        command = tuple(self._build_command(board, resolved_image))
        self.session = QemuSession(board=board, image_path=resolved_image, command=command)

    def run(self) -> None:
        session = self._require_session()
        if session.process is not None and session.process.poll() is None:
            return

        binary = shutil.which(session.command[0])
        if binary is None:
            raise FileNotFoundError(f"QEMU binary '{session.command[0]}' was not found in PATH")

        try:
            session.process = subprocess.Popen(
                session.command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )
        except FileNotFoundError as exc:
            raise FileNotFoundError(
                f"QEMU launch failed because '{session.command[0]}' is not available"
            ) from exc

    def pause(self) -> None:
        session = self._require_session()
        if session.process is None or session.process.poll() is not None:
            raise QemuBackendError("cannot pause a QEMU session that is not running")
        raise QemuBackendError("pause control is not implemented for QEMU sessions yet")

    def stop(self) -> None:
        if self.session is None:
            return

        process = self.session.process
        if process is not None and process.poll() is not None:
            self.session = None
            return
        if process is not None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)

        self.session = None

    def _build_command(self, board: BoardSpec, image_path: Path) -> list[str]:
        binary = str(board.backend_options.get("binary", self.binary))
        board_args = board.backend_options.get("args", ())
        if isinstance(board_args, str):
            board_args = (board_args,)
        elif not isinstance(board_args, (list, tuple)):
            raise QemuBackendError("backend_options.args must be a sequence of strings")

        command = [binary, *self.extra_args, "-machine", board.machine]

        cpu_model = self._cpu_model(board)
        if cpu_model:
            command.extend(["-cpu", cpu_model])

        if board.architecture.startswith("riscv"):
            command.extend(["-bios", "none"])

        if board.backend_options.get("gdb_stub", True):
            command.extend(["-S", "-s"])

        memory = board.backend_options.get("memory")
        if memory:
            command.extend(["-m", str(memory)])

        firmware_flag = self._firmware_flag(board)
        command.extend([firmware_flag, str(image_path)])
        command.extend(str(arg) for arg in board_args)
        return command

    def _cpu_model(self, board: BoardSpec) -> str | None:
        model = board.backend_options.get("cpu_model")
        if model is not None:
            return str(model)
        if board.architecture == "riscv32":
            return "rv32"
        if board.architecture == "riscv64":
            return "max"
        return None

    def _firmware_flag(self, board: BoardSpec) -> str:
        if board.firmware_format == "elf":
            return "-kernel"
        raise QemuBackendError(f"unsupported firmware format for QEMU backend: {board.firmware_format}")

    def _require_session(self) -> QemuSession:
        if self.session is None:
            raise QemuBackendError("no QEMU session has been loaded")
        return self.session
