# Architecture Notes

Boardforge is designed around a backend-neutral core.

The core should not depend on:

- Renode-specific APIs
- QEMU-specific machine names
- A single ISA or vendor family

Backends are expected to adapt a common execution contract to a concrete simulator.
