# Offline NAK probe (P0.2)

This is an isolated host Mesa/NVK build under `out/nak-host-probe`. No production Mesa/SDK sources are changed. `install.py` appends a probe main function only to the snapshot `nvk_shader.c`, enabling access to its real static NVK lowering routines. Meson links the snapshot's real NAK/NVK/NIR sources.

Current status: all four shaders compiled and disassembled. Provisional static metrics in `out/nak-host-probe/results/summary.json`, hashes/reproduction in `out/nak-host-probe/host-probe-manifest.json`. AA:104 GPR,10785 instructions,16 max warps/SM;952E:64/7465/32;C45:64/10465/32;water:96/12936/20. All four:0 local bytes,0 spills/fills. No measured performance gain is implied.

Target: GM20B / Maxwell SM53. Inputs are runtime-cache-derived fragment SPIR-V from `out/runtime-shader-probe/batch-full-depth`. `late` means bit50, even though the filename records the original modification before OR-ing the bit. Water uses the unchanged 0x1100000000FF modification, because it kills and is not eligible for bit50.

Limitations: descriptor layouts are reconstructed from SPIR-V declarations and NVK descriptor size rules. The SDK constant set is filled with all five UBO bindings, including unused vertex constants. Texture and shared-memory array layouts remain reconstructed; validate them against captured pipeline state. RobustBufferAccess is enabled for UBO/SSBO to match run13 startup features. The FS key is zero (no host Z/S self dependency or forced sample shading); run12 cache confirms all four heavy shaders have 1x MSAA and sample_rate_shading=0, matching the zero force_sample_shading key. Driver robustness and reconstructed layouts still need confirmation against hardware counters. Capability acceptance is all enabled, while shader semantics come from the input module. Host compilation is diagnostic, not proof of console correctness/performance. `static_cycles` excludes variable-latency texture/global memory operations and is not GPU elapsed time. Validate GPR/spill/code sizes against the console P0.1 counters before drawing quantitative conclusions.

Build dependencies: `mercenaries2-mesa-build:dev`, host libdrm-dev from bookworm-backports (2.4.123), libelf-dev, libudev-dev, libzstd-dev. Existing READ ONLY native `mesa_clc` and `vtn_bindgen2` executables are used. Host GCC12, Rust1.101 nightly, Meson1.12.1. Reproduce inside image with project mounted at `/work`: `bash /work/tools/nak_host_probe/build.sh` (fresh source snapshot required first).



Host-only source restorations: dlfcn.h in vk_instance.c; existing MAX_CLASSES16 moved before Linux first use. Clang15 library and resource-directory explicitly paired for bindgen; mesa_clc uses the same15/include resource symlink as the Switch build script. Layout logs verify set0 shared binding0 and EDRAMbinding1 both exist for these inputs. Static opcode histograms count generated machine code, including control flow and scheduling NOPs; LD/ST are not EDRAM-only. Core NAK/NIR sources match production hashes in the manifest.


Run13 log017 line25 reports maxStorageBufferRange4294967295; SDK512MiB shared memory therefore has1 descriptor. Logged set0 binding0 count1/stride16/offset0 and binding1 offset16 match the actual SDK layout, not an unknown omission. Constants all5plain UBOs and heavy4MSAA1x/sample_rate_shading0 verified against SDK/cache. Hardware statistic agreement is still pending.

Fresh source snapshot (before install.py), from inside container:
```bash
mkdir -p /work/out/nak-host-probe
cd /work/reference/mesa-switch-src
tar --exclude=./builddir-native --exclude=./builddir-switch --exclude=./.git -cf - . | tar -xf - -C /work/out/nak-host-probe
bash /work/tools/nak_host_probe/build.sh
```

B:88 optional third argument `[ps|vs]` selects standalone shader stage (default PS). VS pipeline linking is not reconstructed; use paired OFF/ON metrics only, not absolute hardware estimates. Evidence `out/track-b/vs-contraction/analysis-result.json`.
