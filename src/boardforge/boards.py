"""Board definition loading for built-in and user-defined boards."""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any

import yaml

from .core import BoardSpec, MemoryRegion, Peripheral


class BoardValidationError(ValueError):
    """Raised when a board definition is missing required data."""


def load_board_spec(path: str | Path) -> BoardSpec:
    """Load a board specification from a YAML or JSON file."""

    board_path = Path(path)
    raw_data = yaml.safe_load(board_path.read_text(encoding="utf-8"))
    if not isinstance(raw_data, dict):
        raise BoardValidationError("board file must contain a mapping at the top level")
    return board_from_mapping(raw_data, source=board_path)


def board_from_mapping(data: dict[str, Any], source: Path | None = None) -> BoardSpec:
    """Normalize a mapping into a validated BoardSpec."""

    required_fields = ("name", "architecture", "cpu", "backend")
    missing = [field for field in required_fields if not data.get(field)]
    if missing:
        joined = ", ".join(missing)
        raise BoardValidationError(f"board definition is missing required fields: {joined}")

    memory_regions = tuple(_parse_memory_region(item) for item in data.get("memory_regions", ()))
    peripherals = tuple(_parse_peripheral(item) for item in data.get("peripherals", ()))

    backend_options = data.get("backend_options", {})
    if not isinstance(backend_options, dict):
        raise BoardValidationError("backend_options must be a mapping")

    return BoardSpec(
        name=str(data["name"]),
        architecture=str(data["architecture"]),
        cpu=str(data["cpu"]),
        backend=str(data["backend"]),
        machine=_optional_str(data.get("machine")),
        vendor=_optional_str(data.get("vendor")),
        description=_optional_str(data.get("description")),
        firmware_format=str(data.get("firmware_format", "elf")),
        memory_regions=memory_regions,
        peripherals=peripherals,
        backend_options=backend_options,
        source=source,
    )


def dump_board_spec(board: BoardSpec) -> dict[str, Any]:
    """Convert a board spec to a serializable mapping."""

    data = asdict(board)
    if board.source is not None:
        data["source"] = str(board.source)
    return data


def _parse_memory_region(data: Any) -> MemoryRegion:
    if not isinstance(data, dict):
        raise BoardValidationError("each memory region must be a mapping")

    required_fields = ("name", "base", "size", "kind")
    missing = [field for field in required_fields if field not in data]
    if missing:
        joined = ", ".join(missing)
        raise BoardValidationError(f"memory region is missing required fields: {joined}")

    return MemoryRegion(
        name=str(data["name"]),
        base=_parse_int(data["base"]),
        size=_parse_int(data["size"]),
        kind=str(data["kind"]),
        permissions=str(data.get("permissions", "rw")),
        file=_optional_str(data.get("file")),
    )


def _parse_peripheral(data: Any) -> Peripheral:
    if not isinstance(data, dict):
        raise BoardValidationError("each peripheral must be a mapping")

    required_fields = ("name", "kind")
    missing = [field for field in required_fields if field not in data]
    if missing:
        joined = ", ".join(missing)
        raise BoardValidationError(f"peripheral is missing required fields: {joined}")

    known_fields = {"name", "kind", "address", "size", "properties"}
    extra_properties = {key: value for key, value in data.items() if key not in known_fields}
    explicit_properties = data.get("properties", {})
    if explicit_properties and not isinstance(explicit_properties, dict):
        raise BoardValidationError("peripheral properties must be a mapping")

    properties = dict(explicit_properties)
    properties.update(extra_properties)

    return Peripheral(
        name=str(data["name"]),
        kind=str(data["kind"]),
        address=_parse_optional_int(data.get("address")),
        size=_parse_optional_int(data.get("size")),
        properties=properties,
    )


def _parse_int(value: Any) -> int:
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        return int(value, 0)
    raise BoardValidationError(f"expected integer-compatible value, got {type(value).__name__}")


def _parse_optional_int(value: Any) -> int | None:
    if value is None:
        return None
    return _parse_int(value)


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)
