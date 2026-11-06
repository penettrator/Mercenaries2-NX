# Building Mercenaries2-NX 0.2.0

[Русский](building.md)

Requires Windows, PowerShell, Python3, Git, Docker Desktop and your own Xbox360 game. Ready-to-use packages do not require a local build; see [README](../README.en.md).

## Dependencies

Run from the repository root. Pinned bases and consolidated patches:

```sh
git clone https://github.com/nebadasSwifty/masseffect-nx.git reference/masseffect-nx
git -C reference/masseffect-nx checkout a85b0b419ec3e332165ae1617c980bd399856a44
git -C reference/masseffect-nx apply ../../patches/rexglue-sdk-masseffect-nx.patch

git clone https://github.com/rexglue/rexglue-sdk.git reference/rexglue-upstream
git -C reference/rexglue-upstream checkout f5337cdc947ff6d4c4196737e2c807a48f2a1fc2
git -C reference/rexglue-upstream submodule update --init --recursive

git clone https://github.com/danfromtico/mesa-switch.git reference/mesa-switch-src
git -C reference/mesa-switch-src checkout d4a00ea0ab3f59afb967cc5d779e4263d237bd77
git -C reference/mesa-switch-src apply ../../patches/mesa-switch.patch
python tools/materialize_dependency_links.py
```

Consolidated `patches/` exports contain the current SDK/Mesa changes. `tools/patches` and patch helpers are checked incremental/build steps; do not manually apply every historical patch over the consolidated export.

## Game data and code generation

Put your extracted game in `assets/game_root/`. Supported `default.xex` SHA-256: `48e805e4a2c1c4f7b409245dc9f2d02e2e8a94eaa0e9f1744d150ddce00bf72b`. Keep the edition's WAD, audio and movie files.

Extract the official Windows ReXGlue0.10.0 SDK from [releases](https://github.com/rexglue/rexglue-sdk/releases) under `tools/bin/` so the script finds `rexglue.exe`.

```powershell
tools/codegen.ps1
```

The script also prepares generated sources. `app/generated/` remains local and must not be committed.

## Switch NVK/Mesa

```powershell
docker build -t mercenaries2-mesa-build:dev -f tools/Dockerfile.mesa tools
tools/continue_switch_build.ps1
```

Output: `out/mesa-sdk/opt/devkitpro/portlibs/switch/lib/libvulkan.a`. This is a lengthy step. Keep build logs in ignored logs/out directories.

## NRO build

```powershell
tools/build_switch.ps1 -Jobs 6 -GlobalOptimizations -SlotSourceEpoch -ImageReuse -MaterialRetention -RingWriteback -NativeTableLookup -Pgo OFF -BuildDirectory out/nx-release
```

The NRO container is pinned by `tools/build_switch.ps1`: `devkitpro/devkita64@sha256:1fc388c3a0d34bd2045a6dadcb1020e069d5f876a187fd705de14b4440c00282` (GCC15.2.0). Output: `out/nx-release/mercenaries2.nro`. Packaging uses `extras/icon.jpg` and NACP version0.2.0.

Copy the NRO and `config/mercenaries2.toml` to `SD:/switch/Mercenaries2/`, and your data to `game_root/`. The normal script explicitly resets unselected experiments, GPU draw profiling, CSV and emulator guards. Keep rejected AlphaCompare/ReadyTextures disabled.

## PGO and the prepared binary

The prepared binary uses PGO USE with 161 original profiles, including the renderer. Two modified native translation units and the new helper TU do not consume old profiles. All 163 original gcda/GEN graphs remain unchanged; the strict final build has zero missing-profile/coverage-mismatch diagnostics. CSV and game-clock diagnostics are disabled.

Raw training data is not distributed. The ordinary command above uses PGO OFF and does not promise identical performance. For your own training use `-Pgo GEN`, a unique `-PgoSession`, the pinned compiler and `tools/pgo_session.py` checks (prepare/finalize/import/audit). Never mix sources/modes or suppress mismatches. `-Pgo USE` requires your own finalized compatible session. See [performance-2026-11-06.md](performance-2026-11-06.md) for the mechanism and limitations.

## HOME forwarder

From Git Bash, using your own console keys:

```sh
SWITCH_PROD_KEYS=/path/to/prod.keys tools/build_forwarder.sh out/nx-release/mercenaries2.nro out/forwarder
```

The script pins Forwarder-Mod/hacBrewPack and the build container. It validates 39-bit addressing and cores0–3 in both ACI0/ACID. Title ID: `014d455243530000`; path: `sdmc:/switch/Mercenaries2/mercenaries2.nro`. Keys are not embedded in the NSP/packages/Git or printed in the build log.

## Cache and validation

Native caches are generated on the console under `mercenaries2/cache/shaders/driver/`. With `mercs2_native_pipeline_prewarm=true` and `mercs2_native_prewarm_before_game=true`, known variants are warmed before Main. Unseen variants still compile on first use. Other games' caches are incompatible. Game caches are excluded from public source/binary packages.

`tools/audit_native_shader_cache.py` validates framing, XXH3 checksums and key references. It needs a host xxHash library (`--hash-library` if needed). Readiness checks: `python tools/test_native_bugfix16.py` on Linux with g++23/ASan/UBSan; native helpers: `python tools/test_native_table_lookup.py`. These use locally generated code from your game; passing them does not replace Switch testing.
