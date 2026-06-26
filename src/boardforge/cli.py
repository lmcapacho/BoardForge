"""Command-line interface for Boardforge."""

from __future__ import annotations

import argparse
import os
from dataclasses import dataclass
from pathlib import Path
import shutil
import subprocess
import sys
import tomllib
from typing import Sequence

from .app import create_default_engine, create_default_registry
from .boards import BoardCatalog


@dataclass(slots=True, frozen=True)
class BuildResult:
    project_path: Path
    command: tuple[str, ...]
    artifacts: tuple[Path, ...]
    returncode: int


@dataclass(slots=True, frozen=True)
class ProjectConfig:
    board: str | None = None
    artifact: str | None = None
    target: str | None = None


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="boardforge")
    subparsers = parser.add_subparsers(dest="command", required=True)

    build_parser = subparsers.add_parser("build", help="Build a firmware project directory")
    build_parser.add_argument("project_dir", help="Firmware project directory")
    build_parser.add_argument("--target", default=None, help="Build target to pass to make")

    doctor_parser = subparsers.add_parser("doctor", help="Check local runtime dependencies and built-in setup")
    doctor_parser.add_argument("--boards-dir", action="append", default=[], help="Additional board search directory")

    list_parser = subparsers.add_parser("list-boards", help="List available board definitions")
    list_parser.add_argument("--boards-dir", action="append", default=[], help="Additional board search directory")

    show_parser = subparsers.add_parser("show-board", help="Show a board definition summary")
    show_parser.add_argument("board", help="Board name or path")
    show_parser.add_argument("--boards-dir", action="append", default=[], help="Additional board search directory")

    prepare_parser = subparsers.add_parser("prepare", help="Prepare a backend session without launching it")
    prepare_parser.add_argument("board", help="Board name or path")
    prepare_parser.add_argument("image", help="Firmware image path")
    prepare_parser.add_argument("--boards-dir", action="append", default=[], help="Additional board search directory")

    run_parser = subparsers.add_parser("run", help="Launch a backend session")
    run_parser.add_argument("board", nargs="?", help="Board name or path")
    run_parser.add_argument("image", nargs="?", help="Firmware image path")
    run_parser.add_argument("--project-dir", help="Firmware project directory to build and infer settings from")
    run_parser.add_argument("--build", action="store_true", help="Build the firmware project before running")
    run_parser.add_argument("--target", default=None, help="Build target to pass to make when --build is used")
    run_parser.add_argument("--boards-dir", action="append", default=[], help="Additional board search directory")
    run_parser.add_argument(
        "--timeout",
        type=float,
        default=2.0,
        help="Seconds to wait for process output before stopping the session if it keeps running",
    )

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "build":
        return _build(args.project_dir, args.target)

    catalog = _build_catalog(args.boards_dir)
    engine = create_default_engine(boards=catalog)

    if args.command == "doctor":
        return _doctor(catalog)
    if args.command == "list-boards":
        return _list_boards(catalog)
    if args.command == "show-board":
        return _show_board(catalog, args.board)
    if args.command == "prepare":
        return _prepare(engine, args.board, args.image)
    if args.command == "run":
        return _run(engine, args.board, args.image, args.project_dir, args.build, args.target, args.timeout)

    parser.error(f"unsupported command: {args.command}")
    return 2


def _build(project_dir: str, target: str | None) -> int:
    build_result = _build_project(Path(project_dir), target)
    if isinstance(build_result, int):
        return build_result
    result, stdout, stderr = build_result
    _print_build_result(result, stdout, stderr)
    if result.returncode != 0:
        print(f"build failed: exit code {result.returncode}")
        return result.returncode
    print("build succeeded")
    return 0


def _build_project(project_dir: Path, target: str | None) -> tuple[BuildResult, str, str] | int:
    project_path = project_dir.resolve()
    makefile = project_path / "Makefile"
    if not project_path.is_dir():
        print(f"build failed: project directory not found: {project_path}")
        return 1
    if not makefile.exists():
        print(f"build failed: Makefile not found in {project_path}")
        return 1

    config = _load_project_config(project_path)
    resolved_target = target or config.target or "all"

    make_path = shutil.which("make")
    if make_path is None:
        print("build failed: make not found in PATH")
        return 1

    command = [make_path]
    if resolved_target:
        command.append(resolved_target)

    result = subprocess.run(command, cwd=project_path, capture_output=True, text=True, check=False)
    artifacts = _resolve_project_artifacts(project_path, config)
    return BuildResult(
        project_path=project_path,
        command=tuple(command),
        artifacts=artifacts,
        returncode=result.returncode,
    ), result.stdout, result.stderr


def _resolve_project_artifacts(project_path: Path, config: ProjectConfig) -> tuple[Path, ...]:
    if config.artifact:
        artifact_path = (project_path / config.artifact).resolve()
        return (artifact_path,) if artifact_path.exists() else ()
    return tuple(sorted(project_path.glob("*.elf")))


def _print_build_result(build_result: BuildResult, stdout: str = "", stderr: str = "") -> None:
    print(f"project: {build_result.project_path}")
    print(f"command: {' '.join(build_result.command)}")
    if stdout:
        print(stdout, end="" if stdout.endswith("\n") else "\n")
    if stderr:
        print(stderr, end="" if stderr.endswith("\n") else "\n")
    if build_result.artifacts:
        print("artifacts:")
        for artifact in build_result.artifacts:
            print(artifact)
        print(f"primary-artifact: {build_result.artifacts[0]}")


def _resolve_run_request(
    board: str | None,
    image: str | None,
    project_dir: str | None,
    build: bool,
    target: str | None,
) -> tuple[str, Path, bool]:
    config = ProjectConfig()
    project_path: Path | None = None
    inferred_image = False
    inferred_board = False

    if project_dir:
        project_path = Path(project_dir).resolve()
        config = _load_project_config(project_path)

    if build:
        if project_path is None:
            print("run failed: --build requires --project-dir")
            raise SystemExit(1)
        build_result = _build_project(project_path, target)
        if isinstance(build_result, int):
            raise SystemExit(build_result)
        result, stdout, stderr = build_result
        _print_build_result(result, stdout, stderr)
        if result.returncode != 0:
            print(f"build failed: exit code {result.returncode}")
            raise SystemExit(result.returncode)
        if not result.artifacts:
            print(f"run failed: no .elf artifacts found in {result.project_path}")
            raise SystemExit(1)
        print("build succeeded")
        resolved_image = result.artifacts[0]
        inferred_image = image is None
    elif project_path is not None:
        artifacts = _resolve_project_artifacts(project_path, config)
        if not artifacts:
            print(f"run failed: no .elf artifacts found in {project_path}")
            raise SystemExit(1)
        resolved_image = artifacts[0]
        inferred_image = image is None
    elif image is not None:
        resolved_image = Path(image)
    else:
        print("run failed: provide an image path or use --project-dir")
        raise SystemExit(1)

    resolved_board = board or config.board
    if resolved_board is None:
        print("run failed: provide a board name/path or define board in boardforge.toml")
        raise SystemExit(1)
    inferred_board = board is None

    if image is not None:
        resolved_image = Path(image)
        inferred_image = False

    return resolved_board, resolved_image, inferred_image or inferred_board


def _load_project_config(project_path: Path) -> ProjectConfig:
    config_path = project_path / "boardforge.toml"
    if not config_path.exists():
        return ProjectConfig()

    raw = tomllib.loads(config_path.read_text(encoding="utf-8"))
    data = raw.get("project")
    if not isinstance(data, dict):
        return ProjectConfig()

    board = data.get("board")
    artifact = data.get("artifact")
    target = data.get("target")
    return ProjectConfig(
        board=str(board) if board is not None else None,
        artifact=str(artifact) if artifact is not None else None,
        target=str(target) if target is not None else None,
    )


def _build_catalog(extra_dirs: Sequence[str]) -> BoardCatalog:
    catalog = BoardCatalog.default()
    for directory in extra_dirs:
        catalog = catalog.add_search_path(directory)
    return catalog


def _doctor(catalog: BoardCatalog) -> int:
    failures = 0
    registry = create_default_registry()
    boards = catalog.list()

    failures += _report_check("python", True, sys.executable)
    failures += _report_check("venv", sys.prefix != sys.base_prefix, sys.prefix)
    failures += _report_check("boards", len(boards) > 0, f"{len(boards)} discovered")
    failures += _report_check("backends", len(registry.names()) > 0, ", ".join(registry.names()))

    failures += _report_binary("qemu-system-riscv32", ["qemu-system-riscv32", "--version"])
    failures += _report_binary("renode", ["/usr/bin/renode", "--version"], binary_name="renode")
    failures += _report_binary("dotnet", ["dotnet", "--info"])

    if failures:
        print(f"summary: {failures} check(s) failed")
        return 1

    print("summary: all checks passed")
    return 0


def _report_binary(label: str, version_command: list[str], binary_name: str | None = None) -> int:
    name = binary_name or version_command[0]
    path = shutil.which(name)
    if path is None and os.path.isabs(version_command[0]) and os.path.exists(version_command[0]):
        path = version_command[0]
    if path is None:
        return _report_check(label, False, "not found in PATH")

    try:
        result = subprocess.run(version_command, capture_output=True, text=True, timeout=5, check=False)
    except Exception as exc:
        return _report_check(label, False, f"present at {path}, version probe failed: {exc}")

    first_line = _first_non_empty_line(result.stdout) or _first_non_empty_line(result.stderr) or "version probe returned no output"
    ok = result.returncode == 0
    detail = f"{path} | {first_line}"
    return _report_check(label, ok, detail)


def _first_non_empty_line(value: str) -> str | None:
    for line in value.splitlines():
        stripped = line.strip()
        if stripped:
            return stripped
    return None


def _report_check(name: str, ok: bool, detail: str) -> int:
    status = "OK" if ok else "FAIL"
    print(f"[{status}] {name}: {detail}")
    return 0 if ok else 1


def _list_boards(catalog: BoardCatalog) -> int:
    for board in catalog.list():
        description = board.description or ""
        print(f"{board.name}\t{board.backend}\t{board.architecture}\t{description}")
    return 0


def _show_board(catalog: BoardCatalog, board_ref: str) -> int:
    board = catalog.resolve(board_ref)
    print(f"name: {board.name}")
    print(f"backend: {board.backend}")
    print(f"architecture: {board.architecture}")
    print(f"cpu: {board.cpu}")
    if board.machine:
        print(f"machine: {board.machine}")
    if board.description:
        print(f"description: {board.description}")
    if board.source:
        print(f"source: {board.source}")
    return 0


def _prepare(engine, board_ref: str, image: str) -> int:
    session = engine.load(board_ref, image)
    print(f"prepared: {session.board.name}")
    print(f"backend: {session.backend_name}")
    print(f"image: {session.image_path}")
    print(f"state: {engine.state.value}")
    backend = engine.active_backend
    backend_session = getattr(backend, "session", None)
    if backend_session is not None:
        command = getattr(backend_session, "command", None)
        if command is not None:
            print(f"command: {' '.join(command)}")
    return 0


def _run(
    engine,
    board_ref: str | None,
    image: str | None,
    project_dir: str | None,
    build: bool,
    target: str | None,
    timeout: float,
) -> int:
    try:
        resolved_board, resolved_image, inferred = _resolve_run_request(
            board_ref, image, project_dir, build, target
        )
    except SystemExit as exc:
        return int(exc.code)

    if inferred:
        print(f"resolved-board: {resolved_board}")
        print(f"resolved-image: {resolved_image}")

    session = engine.load(resolved_board, resolved_image)
    try:
        engine.run()
    except Exception as exc:
        print(f"launch failed: {exc}")
        return 1

    print(f"running: {session.board.name}")
    print(f"backend: {session.backend_name}")
    print(f"image: {session.image_path}")
    print(f"state: {engine.state.value}")

    backend = engine.active_backend
    backend_session = getattr(backend, "session", None)
    command = getattr(backend_session, "command", None)
    process = getattr(backend_session, "process", None)
    if command is not None:
        print(f"command: {' '.join(command)}")
    if process is None or process.stdout is None:
        return 0

    try:
        stdout, _ = process.communicate(timeout=timeout)
        if stdout:
            print(stdout, end="" if stdout.endswith("\n") else "\n")
        print(f"exit-code: {process.returncode}")
        return process.returncode or 0
    except subprocess.TimeoutExpired as exc:
        partial_stdout = exc.stdout or ""
        if isinstance(partial_stdout, bytes):
            partial_stdout = partial_stdout.decode(errors="replace")
        if partial_stdout:
            print(partial_stdout, end="" if partial_stdout.endswith("\n") else "\n")
        print(f"timeout: process still running after {timeout:.1f}s")
        engine.stop()
        try:
            leftover_stdout, _ = process.communicate(timeout=1)
        except Exception:
            leftover_stdout = ""
        if isinstance(leftover_stdout, bytes):
            leftover_stdout = leftover_stdout.decode(errors="replace")
        if leftover_stdout:
            print(leftover_stdout, end="" if leftover_stdout.endswith("\n") else "\n")
        print("session stopped")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
