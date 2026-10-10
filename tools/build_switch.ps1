param([int]$Jobs = 4, [string]$Image = 'devkitpro/devkita64:latest')
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$driver = Join-Path $projectRoot 'out/mesa-sdk/opt/devkitpro/portlibs/switch/lib/libvulkan.a'
if (-not (Test-Path -LiteralPath $driver)) { throw 'Missing NVK driver: out/mesa-sdk/opt/devkitpro/portlibs/switch/lib/libvulkan.a' }
python (Join-Path $PSScriptRoot 'materialize_dependency_links.py')
if ($LASTEXITCODE) { throw 'Dependency preparation failed' }
python (Join-Path $PSScriptRoot 'apply_sdk_patches.py')
if ($LASTEXITCODE) { throw 'Switch SDK patch preparation failed' }
python (Join-Path $PSScriptRoot 'prepare_switch_codegen.py')
if ($LASTEXITCODE) { throw 'Switch codegen preparation failed' }
& docker run --rm --mount "type=bind,source=$projectRoot,target=/work" -w /work $Image bash -lc "cmake -S app -B out/nx -G Ninja -DCMAKE_BUILD_TYPE=Release -DCMAKE_TOOLCHAIN_FILE=/work/tools/switch/cmake/switch-devkitA64.cmake -DREXSDK_DIR=/work/reference/masseffect-nx/sdk -DREXGLUE_SWITCH_NVK_SDK=/work/out/mesa-sdk/opt/devkitpro/portlibs/switch && cmake --build out/nx --target mercenaries2 -j $Jobs"
if ($LASTEXITCODE) { throw 'Switch build failed' }
