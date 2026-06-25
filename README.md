# Boardforge

Boardforge is a neutral simulation workspace for embedded boards.

The project is intended to support:

- Multiple instruction set architectures, including RISC-V.
- Multiple simulation backends, including Renode and QEMU.
- Built-in boards and user-defined custom boards.
- A stable engine API for editors, IDE integrations, and teaching tools.

## Goals

- Keep the core independent from any single board vendor.
- Avoid depending on patched emulator forks.
- Represent boards declaratively when possible.
- Support different fidelity levels, from generic SoC simulation to board-specific emulation.

## Planned Architecture

- `src/boardforge/core`
  Core domain models, engine contracts, and orchestration.
- `src/boardforge/backends`
  Backend adapters for Renode, QEMU, and future simulators.
- `src/boardforge/boards`
  Built-in board definitions and loaders for user board specs.
- `docs/`
  Design notes and architecture decisions.

## Initial Scope

The first iterations should focus on:

1. A backend-neutral engine interface.
2. A board specification format.
3. A first Renode backend.
4. An optional QEMU backend for generic targets.

## License

This project uses the GNU General Public License v3.0, matching the earlier prototype work.
