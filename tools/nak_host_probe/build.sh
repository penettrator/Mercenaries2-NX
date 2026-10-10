#!/usr/bin/env bash
# Run inside mercenaries2-nak-host:dev with project mounted at /work.
set -euo pipefail
export PATH=/work/reference/mesa-switch-src/builddir-native/src/compiler/clc:/work/reference/mesa-switch-src/builddir-native/src/compiler/spirv:$PATH
export LIBCLANG_PATH=/usr/lib/llvm-15/lib
export BINDGEN_EXTRA_CLANG_ARGS=-resource-dir=/usr/lib/llvm-15/lib/clang/15.0.6
if [ ! -d /usr/lib/llvm-15/lib/clang/15/include ]; then
  mkdir -p /usr/lib/llvm-15/lib/clang/15
  ln -s /usr/lib/llvm-15/lib/clang/15.0.6/include /usr/lib/llvm-15/lib/clang/15/include
fi
python3 /work/tools/nak_host_probe/install.py
cd /work/out/nak-host-probe
meson setup build --reconfigure -Dvulkan-drivers=nouveau -Dgallium-drivers= -Dplatforms= -Dglx=disabled -Degl=disabled -Dopengl=false -Dgles1=disabled -Dgles2=disabled -Dllvm=disabled -Dmesa-clc=system -Dprecomp-compiler=system -Dbuildtype=release > setup.log 2>&1
ninja -j4 -C build src/nouveau/vulkan/nak-host-probe > build.log 2>&1
mkdir -p results
probe=build/src/nouveau/vulkan/nak-host-probe
inputs=/work/out/runtime-shader-probe/batch-full-depth
for input in 3E0AB1A6A7CD8CFB-0000000000000003-late 952E55BBBE85A6F4-0000000000000003-late C45C07BB16BF2E70-0000050000000003-late 9AD799B034BB706F-00001100000000FF-unchanged; do
  "$probe" "$inputs/$input.spv" "results/$input" > "results/$input.log" 2>&1
done



python3 /work/tools/nak_host_probe/summarize.py
python3 /work/tools/nak_host_probe/manifest.py

