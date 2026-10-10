# Native renderer (Mercenaries 2)

Copied from project8-sw (https://github.com/R-drg/project8-sw, commit 3393f261,
`src/game/src/native/`), which adapts the native renderer of nfsmw-nx
(https://github.com/StevensND/nfsmw-nx). **GPL-3.0-or-later** — this directory keeps the
original SPDX headers; distributing a build that contains it makes the port GPL-3.0.

Renamed: `thps_*` → `mercs2_*` (files, namespace, cvars). Selected with
`mercs2_renderer = "native"` in `mercenaries2.toml`; the default stays the SDK's FSI emulation.
Plan and Mercenaries 2-specific extensions: `PLAN_NATIVE_RENDERER.md` (EDRAM census, HANDOFF §47).
