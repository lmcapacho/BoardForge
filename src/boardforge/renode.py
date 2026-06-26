"""Renode backend adapter."""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from .core import BoardSpec


class RenodeBackendError(RuntimeError):
    """Raised when the Renode backend cannot prepare or control a session."""


@dataclass(slots=True)
class RenodeSession:
    """Prepared Renode launch data for a board execution session."""

    board: BoardSpec
    image_path: Path
    platform_path: Path
    script_path: Path
    command: tuple[str, ...]
    workspace: tempfile.TemporaryDirectory[str]
    process: subprocess.Popen[str] | None = None


class RenodeBackend:
    """Minimal Renode backend that prepares a launchable session."""

    name = "renode"

    def __init__(self, binary: str = "renode", extra_args: Sequence[str] | None = None) -> None:
        self.binary = binary
        self.extra_args = tuple(extra_args) if extra_args is not None else ("--console", "--disable-xwt", "--port", "-1")
        self.session: RenodeSession | None = None

    def load(self, board: BoardSpec, image_path: str | Path) -> None:
        if board.backend != self.name:
            raise RenodeBackendError(
                f"board '{board.name}' targets backend '{board.backend}', not '{self.name}'"
            )

        platform_option = board.backend_options.get("platform")
        if not platform_option:
            raise RenodeBackendError(
                "renode boards must define backend_options.platform with a .repl/.resc platform path"
            )

        if self.session is not None:
            self.stop()

        resolved_image = Path(image_path).resolve()
        platform_path = self._resolve_board_path(board, platform_option)
        workspace = tempfile.TemporaryDirectory(prefix="boardforge-renode-")
        script_path = Path(workspace.name) / "boardforge.resc"
        script_path.write_text(self._build_script(board, platform_path, resolved_image), encoding="utf-8")

        command = tuple(self._build_command(board, script_path))
        self.session = RenodeSession(
            board=board,
            image_path=resolved_image,
            platform_path=platform_path,
            script_path=script_path,
            command=command,
            workspace=workspace,
        )

    def run(self) -> None:
        session = self._require_session()
        if session.process is not None and session.process.poll() is None:
            return

        binary = shutil.which(session.command[0])
        if binary is None:
            raise FileNotFoundError(f"Renode binary '{session.command[0]}' was not found in PATH")

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
                f"Renode launch failed because '{session.command[0]}' is not available"
            ) from exc

    def pause(self) -> None:
        session = self._require_session()
        if session.process is None or session.process.poll() is not None:
            raise RenodeBackendError("cannot pause a Renode session that is not running")
        raise RenodeBackendError("pause control is not implemented for Renode sessions yet")

    def stop(self) -> None:
        if self.session is None:
            return

        process = self.session.process
        if process is not None and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)

        self.session.workspace.cleanup()
        self.session = None

    def _build_command(self, board: BoardSpec, script_path: Path) -> list[str]:
        binary = str(board.backend_options.get("binary", self.binary))
        board_args = board.backend_options.get("args", ())
        if isinstance(board_args, str):
            board_args = (board_args,)
        elif not isinstance(board_args, (list, tuple)):
            raise RenodeBackendError("backend_options.args must be a sequence of strings")

        return [binary, *self.extra_args, *[str(arg) for arg in board_args], str(script_path)]

    def _build_script(self, board: BoardSpec, platform_path: Path, image_path: Path) -> str:
        commands = [
            "mach create",
            f'machine LoadPlatformDescription @{platform_path}',
            f'sysbus LoadELF @{image_path}',
        ]
        extra_commands = board.backend_options.get("monitor_commands", ())
        if isinstance(extra_commands, str):
            extra_commands = (extra_commands,)
        elif not isinstance(extra_commands, (list, tuple)):
            raise RenodeBackendError(
                "backend_options.monitor_commands must be a sequence of monitor commands"
            )
        commands.extend(str(command) for command in extra_commands)
        return "\n".join(commands) + "\n"

    def _resolve_board_path(self, board: BoardSpec, raw_path: str | Path) -> Path:
        candidate = Path(raw_path)
        if candidate.is_absolute():
            return candidate
        if board.source is not None:
            return (board.source.parent / candidate).resolve()
        return candidate.resolve()

    def _require_session(self) -> RenodeSession:
        if self.session is None:
            raise RenodeBackendError("no Renode session has been loaded")
        return self.session
