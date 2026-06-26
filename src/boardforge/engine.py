"""Backend-neutral engine orchestration."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from .backends import BackendRegistry
from .boards import BoardCatalog
from .core import Backend, BoardSpec


class EngineState(str, Enum):
    """Execution lifecycle tracked by the engine."""

    IDLE = "idle"
    LOADED = "loaded"
    RUNNING = "running"
    PAUSED = "paused"


@dataclass(slots=True, frozen=True)
class EngineSession:
    """Current engine session snapshot."""

    board: BoardSpec
    image_path: Path
    backend_name: str


class Engine:
    """Coordinates board loading and backend execution."""

    def __init__(self, backends: BackendRegistry, boards: BoardCatalog | None = None) -> None:
        self._backends = backends
        self._boards = boards or BoardCatalog.default()
        self._state = EngineState.IDLE
        self._session: EngineSession | None = None

    @property
    def state(self) -> EngineState:
        return self._state

    @property
    def session(self) -> EngineSession | None:
        return self._session

    @property
    def active_backend(self) -> Backend | None:
        if self._session is None:
            return None
        return self._backends.get(self._session.backend_name)

    def load(self, board: BoardSpec | str | Path, image_path: str | Path) -> EngineSession:
        resolved_board = self._resolve_board(board)
        resolved_image = Path(image_path)
        backend = self._backend_for_board(resolved_board)
        backend.load(resolved_board, resolved_image)

        self._session = EngineSession(
            board=resolved_board,
            image_path=resolved_image,
            backend_name=resolved_board.backend,
        )
        self._state = EngineState.LOADED
        return self._session

    def run(self) -> None:
        backend = self._require_backend_session({EngineState.LOADED, EngineState.PAUSED})
        backend.run()
        self._state = EngineState.RUNNING

    def pause(self) -> None:
        backend = self._require_backend_session({EngineState.RUNNING})
        backend.pause()
        self._state = EngineState.PAUSED

    def stop(self) -> None:
        backend = self._require_backend_session(
            {EngineState.LOADED, EngineState.RUNNING, EngineState.PAUSED}
        )
        backend.stop()
        self._session = None
        self._state = EngineState.IDLE

    def _resolve_board(self, board: BoardSpec | str | Path) -> BoardSpec:
        return self._boards.resolve(board)

    def _backend_for_board(self, board: BoardSpec) -> Backend:
        return self._backends.get(board.backend)

    def _require_backend_session(self, allowed_states: set[EngineState]) -> Backend:
        if self._session is None or self._state not in allowed_states:
            joined = ", ".join(state.value for state in sorted(allowed_states, key=lambda s: s.value))
            raise RuntimeError(f"engine state must be one of: {joined}")
        return self._backends.get(self._session.backend_name)
