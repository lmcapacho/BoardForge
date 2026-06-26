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

## First Real Runs

Build the included QEMU sample firmware:

```bash
cd /home/lmcapacho/Documents/Projects/boardforge
source .venv/bin/activate
boardforge build examples/qemu-virt-rv32
```

Run it with the built-in QEMU board:

```bash
boardforge doctor
boardforge run qemu-virt-rv32 examples/qemu-virt-rv32/hello_uart.elf --timeout 1.0
```

Or build and run in one step:

```bash
boardforge run qemu-virt-rv32 --project-dir examples/qemu-virt-rv32 --build --timeout 1.0
```

Build the included Renode sample firmware:

```bash
boardforge build examples/renode-rv32-virt
```

Run it with the built-in Renode board:

```bash
boardforge run renode-rv32-virt examples/renode-rv32-virt/hello_uart.elf --timeout 4.0
```

Or build and run in one step:

```bash
boardforge run renode-rv32-virt --project-dir examples/renode-rv32-virt --build --timeout 4.0
```

Both flows should print a line from the emulated firmware through the board UART.

## License

This project uses the GNU General Public License v3.0, matching the earlier prototype work.
