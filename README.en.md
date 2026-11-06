# Mercenaries 2: World in Flames for Nintendo Switch — 0.2.0

[Русский](README.md)

Port author: [penettrator](https://github.com/penettrator). Support: [Boosty](https://boosty.to/itgenius). Donations help fund new ports.

A native port of the Xbox 360 version of Mercenaries 2: World in Flames to Nintendo Switch: PowerPC-to-ARM64 static recompilation with ReXGlue and a native Vulkan renderer using NVK/Mesa. You need your own official copy; public port downloads do not include game data or game shader caches.

## Changes

- Optimized native CPU table helpers and renderer work, with PGO.
- Reduced repeated texture allocations and added bounded material/image caches.
- Fixed slow movement, camera and animation in the tested interior by removing the port's extra 30 FPS limit.
- Referenced textures wait for their existing upload job instead of using an empty placeholder.
- Recorded shader/pipeline variants are warmed before gameplay. Test frame capture and game-clock diagnostics are disabled.

## Requirements

- Nintendo Switch running Atmosphère.
- At least **8 GB** free on SD; FAT32 works.
- DBI or another NSP installer.
- Your own Xbox 360 game. Supported `default.xex` SHA-256: `48e805e4a2c1c4f7b409245dc9f2d02e2e8a94eaa0e9f1744d150ddce00bf72b`.

## Installation

### 1. Port files

Ready-to-use files are distributed through [Releases](https://github.com/penettrator/Mercenaries2-NX/releases):

| File | Purpose |
|---|---|
| `Mercenaries2-NX.zip` | Port, settings and VERSION: `switch/Mercenaries2/` |
| `Mercenaries2-forwarder.nsp` | HOME icon; permits all four CPU cores |

Extract the ZIP to the SD root. You should get `SD:/switch/Mercenaries2/`, without an extra `switch/switch` directory. You do not need to compile the port to install it.

### 2. Your game

If already extracted, name the folder containing `default.xex` **`game_root`**. Otherwise extract your Xbox 360 ISO using [extract-xiso](https://github.com/XboxDev/extract-xiso/releases):

```text
extract-xiso.exe -x "Mercenaries 2.iso" -d game_root
```

Copy the entire `game_root` into `SD:/switch/Mercenaries2/`. It must contain `default.xex`, `vz.wad`, `shell.wad`, `audios`, `movies` and the remaining edition files. `$SystemUpdate` is not required.

```text
SD:/switch/Mercenaries2/
  mercenaries2.nro
  mercenaries2.toml
  VERSION
  game_root/
    default.xex
    vz.wad
    ...remaining game files
```

### 3. Start

Install **Mercenaries2-forwarder.nsp** using DBI and launch from HOME without holding R. It loads the NRO from SD, so keep the game directory on the card.

**The forwarder already permits all four cores. No `atmosphere/hbl.nsp` replacement or system-file edits are needed.**

Alternatively, hold R while starting a normal installed game, wait for hbmenu and select Mercenaries 2. Fourth-core access depends on your loader. **Do not launch through Album:** applet memory is insufficient.

## Updating an older version

1. Fully close the game: HOME → X → Close.
2. Back up `SD:/switch/Mercenaries2/mercenaries2/` (saves and cache) and your old TOML to your computer.
3. Replace only `mercenaries2.nro`, `mercenaries2.toml` and `VERSION` inside `SD:/switch/Mercenaries2/` using the new ZIP.
4. Install the new forwarder over the old one and choose Continue.

You do not need to copy `game_root` again. Keep the existing game folder and nested `mercenaries2` folder, which holds saves. Reapply language and other personal settings to the new TOML; do not restore the entire old config.

## Settings

File: **`SD:/switch/Mercenaries2/mercenaries2.toml`**. Fully restart after edits.

| Setting | Value | Purpose |
|---|---|---|
| `user_language` | `12` | `12` Russian, `1` English; available text/audio depends on edition |
| `present_effect` | `"fsr"` | FSR 1, internal resolution 960×544 |
| `achievement_notifications` | `false` | Achievement popups disabled |
| `mercs2_min_frame_vblanks` | `1` | Preserve guest frame cadence, including interiors |
| `mercs2_native_texture_demand_wait` | `true` | Wait for referenced textures instead of empty materials |
| `mercs2_native_prewarm_before_game` | `true` | Warm known pipelines before gameplay |

Testing used handheld CPU1785 / GPU768 / RAM2200 MHz. The port does not set clocks; this measurement profile is not a universal requirement for every Switch revision.

## Known limitations

- Entering a new area may still cause frame drops and brief building-material flicker. Complete elimination of that defect is unconfirmed.
- Prewarm covers recorded variants; unseen shaders and pipeline states may still compile on first use. A first run without a personal cache may be less smooth.
- The configuration retains three shadow cascades and the previous effect settings; distant shadows are limited relative to the original.

## Source, credits and licenses

Developer instructions: [Russian build guide](docs/building.md), [English build guide](docs/building.en.md). Version changes: [CHANGELOG.md](CHANGELOG.md). Generated code, game images, saves, raw PGO data and game caches are excluded from Git.

- [ReXGlue SDK](https://github.com/rexglue/rexglue-sdk) / [Xenia](https://xenia.jp).
- [masseffect-nx](https://github.com/nebadasSwifty/masseffect-nx).
- [project8-sw](https://github.com/R-drg/project8-sw), [the-simpsons-game-nx](https://github.com/R-drg/the-simpsons-game-nx), [NFSMW-NX](https://github.com/StevensND/NFSMW-NX).
- [Prototype2-NX](https://github.com/penettrator/Prototype2-NX) — shared renderer and optimization work.
- [mesa-switch](https://github.com/danfromtico/mesa-switch) / [Mesa](https://mesa3d.org).
- [AMD FidelityFX FSR 1](https://github.com/GPUOpen-Effects/FidelityFX-FSR).
- [Forwarder-Mod](https://github.com/Skywalker25/Forwarder-Mod) / nx-hbloader, [hacBrewPack](https://github.com/rlaphoenix/hacBrewPack).

Port code: GPL-3.0, see [LICENSE](LICENSE). Third-party components: [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md), [forwarder license](LICENSE-Forwarder-Mod.txt). Not affiliated with Electronic Arts, Pandemic Studios, Microsoft or Nintendo.
