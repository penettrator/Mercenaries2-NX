# Isolated runtime SPIR-V probe

This uses the actual SDK translator and raw XESH microcode copied read-only from
Switch. It is not the XenosRecomp HLSL tool and does not execute the game.
Only root coordinates device access and hardware test requests.

Inside Docker devkitpro/devkita64 with project mounted at /work:
- `python3 tools/runtime_shader_probe/build.py baseline --reuse` uses retained baseline snapshot.
- `python3 tools/runtime_shader_probe/build.py candidate --snapshot` snapshots current SDK then compiles.
- `out/runtime-shader-probe/candidate/probe INPUT OUTPUT_PREFIX MOD_HEX all fsi` translates a pixel shader.
- `python3 tools/runtime_shader_probe/check_cached_variants.py translate` validates stored pipeline hashes and compares actual cached PS variants.

Inside existing mercenaries2-mesa-build:dev image:
- `python3 tools/runtime_shader_probe/check_cached_variants.py validate`
- `spirv-dis --raw-id FILE.spv -o FILE.spvasm`

Host Python CFG check:
`python tools/runtime_shader_probe/check_interlock.py FILE.spvasm --output REPORT.json`

The validator needs --scalar-block-layout because run10 device explicitly enabled
scalarBlockLayout. Probe profile all=true, SPIRV1.5, native2xfalse matches runtime
translator features. Harness/source/header hashes are saved in out/runtime-shader-probe.
The CFG check intentionally rejects calls and verifies inline depth-AA main only.
Do not overwrite snapshots or edit shared SDK files while any live-source build runs.
The forced candidate batch does not prove current draw-state eligibility or speed.

B:88 optional trailing arguments: `[signs|universal] [ps|vs] [precise|contract]`. Defaults preserve PS/precise; VS comparison evidence `out/track-b/vs-contraction/analysis-result.json`. No production SDK changes.
