param(
    [int]$Jobs = 4,
    [string]$Image = 'devkitpro/devkita64@sha256:1fc388c3a0d34bd2045a6dadcb1020e069d5f876a187fd705de14b4440c00282',
    [switch]$DescriptorBatch, [switch]$LeanDrawTimers, [switch]$FrameCsv,
    [switch]$IndexUploadSpecialization, [switch]$DynamicUploadStamps, [switch]$TargetedMemo,
    [switch]$DepthAttachmentOnly, [switch]$AlphaCompareSpecialization,
    [switch]$LookupFrameCsv, [switch]$NativeTableLookup, [switch]$GlobalOptimizations, [switch]$SlotSourceEpoch, [switch]$ImageReuse, [switch]$ReadyTextures, [switch]$MaterialRetention, [switch]$RingWriteback,
    [ValidateSet('OFF','GEN','USE')][string]$Pgo = 'OFF',
    [string]$PgoSession = '', [string]$BuildDirectory = '', [switch]$PgoSkipTextures, [switch]$PgoSkipNativeSystem, [switch]$PgoSkipRenderer, [string]$PgoDataSession = ''
)
$ErrorActionPreference = 'Stop'
if ($ReadyTextures) { throw 'ReadyTextures rejected: count-cap bypass can cause unbounded creation work; use the bounded runtime sync budget instead' }
if (($PgoSkipNativeSystem -or $PgoSkipRenderer -or $PgoDataSession) -and $Pgo -ne 'USE') { throw 'PGO exclusions/data references require USE' }
if ($PgoDataSession -and $PgoDataSession -notmatch '^[A-Za-z0-9_-]+$') { throw 'Unsafe PgoDataSession' }
if (-not $PgoDataSession) { $PgoDataSession = $PgoSession }
if ($PgoSkipTextures -and $Pgo -ne 'USE') { throw 'PgoSkipTextures requires USE' }
if ($GlobalOptimizations) {
    if ($AlphaCompareSpecialization) { throw 'GlobalOptimizations excludes the rejected alpha experiment (B-003)' }
    $DescriptorBatch = [switch]$true
    $LeanDrawTimers = [switch]$true
    $IndexUploadSpecialization = [switch]$true
    $DynamicUploadStamps = [switch]$true
    $TargetedMemo = [switch]$true
    $DepthAttachmentOnly = [switch]$true
}
$projectRoot = Split-Path -Parent $PSScriptRoot
if ($Pgo -ne 'OFF') {
    if ($PgoSession -notmatch '^[A-Za-z0-9_-]+$') { throw 'PGO requires an explicit safe -PgoSession name' }
    if ($Image -notmatch '@sha256:[a-f0-9]{64}$') { throw 'PGO requires an immutable Docker image digest' }
    if (-not $BuildDirectory) { $BuildDirectory = "out/nx-pgo-$PgoSession" }
} elseif (-not $BuildDirectory) { $BuildDirectory = 'out/nx' }
if ($BuildDirectory -notmatch '^out/[A-Za-z0-9_./-]+$' -or $BuildDirectory -match '(^|/)\.\.(/|$)') {
    throw 'BuildDirectory must be a safe project-relative directory under out/'
}
$driver = Join-Path $projectRoot 'out/mesa-sdk/opt/devkitpro/portlibs/switch/lib/libvulkan.a'
if (-not (Test-Path -LiteralPath $driver)) { throw 'Missing NVK driver: out/mesa-sdk/opt/devkitpro/portlibs/switch/lib/libvulkan.a' }
python (Join-Path $PSScriptRoot 'materialize_dependency_links.py')
if ($LASTEXITCODE) { throw 'Dependency preparation failed' }
python (Join-Path $PSScriptRoot 'apply_sdk_patches.py')
if ($LASTEXITCODE) { throw 'Switch SDK patch preparation failed' }
python (Join-Path $PSScriptRoot 'prepare_switch_codegen.py')
if ($LASTEXITCODE) { throw 'Switch codegen preparation failed' }
if ($Pgo -ne 'OFF') {
    python (Join-Path $PSScriptRoot 'pgo_session.py') prepare --stage $Pgo --session $PgoSession --data-session $PgoDataSession --image $Image --build $BuildDirectory --source-epoch $([int]$SlotSourceEpoch.IsPresent) --texture-features "$([int]$ImageReuse.IsPresent)$([int]$ReadyTextures.IsPresent)" --skip-texture-profile $([int]$PgoSkipTextures.IsPresent) --skip-native-system-profile $([int]$PgoSkipNativeSystem.IsPresent) --skip-renderer-profile $([int]$PgoSkipRenderer.IsPresent) --native-table-lookup $([int]$NativeTableLookup.IsPresent) --lookup-frame-csv $([int]$LookupFrameCsv.IsPresent) --retention-ring-features "$([int]$MaterialRetention.IsPresent)$([int]$RingWriteback.IsPresent)" --features "$([int]$DescriptorBatch.IsPresent)$([int]$LeanDrawTimers.IsPresent)$([int]$IndexUploadSpecialization.IsPresent)$([int]$DynamicUploadStamps.IsPresent)$([int]$TargetedMemo.IsPresent)$([int]$DepthAttachmentOnly.IsPresent)$([int]$AlphaCompareSpecialization.IsPresent)$([int]$FrameCsv.IsPresent)"
    if ($LASTEXITCODE) { throw 'PGO session identity/data validation failed' }
}
$perfOptions = "-DMERCENARIES2_GPU_DRAW_TIMING=OFF -DMERCENARIES2_DESCRIPTOR_BATCH=$([int]$DescriptorBatch.IsPresent) -DMERCENARIES2_LEAN_DRAW_TIMERS=$([int]$LeanDrawTimers.IsPresent) -DMERCENARIES2_FRAME_CSV=$([int]$FrameCsv.IsPresent)"
$perfOptions += " -DMERCENARIES2_INDEX_UPLOAD_SPECIALIZATION=$([int]$IndexUploadSpecialization.IsPresent) -DMERCENARIES2_DYNAMIC_UPLOAD_STAMPS=$([int]$DynamicUploadStamps.IsPresent) -DMERCENARIES2_TARGETED_MEMO=$([int]$TargetedMemo.IsPresent)"
$perfOptions += " -DMERCENARIES2_DEPTH_ATTACHMENT_ONLY=$([int]$DepthAttachmentOnly.IsPresent)"
$perfOptions += " -DMERCENARIES2_ALPHA_COMPARE_SPECIALIZATION=$([int]$AlphaCompareSpecialization.IsPresent)"
$perfOptions += " -DMERCENARIES2_SLOT_SOURCE_EPOCH=$([int]$SlotSourceEpoch.IsPresent)"
$perfOptions += " -DMERCENARIES2_IMAGE_REUSE=$([int]$ImageReuse.IsPresent) -DMERCENARIES2_READY_TEXTURES=$([int]$ReadyTextures.IsPresent)"
$perfOptions += " -DMERCENARIES2_MATERIAL_RETENTION=$([int]$MaterialRetention.IsPresent) -DMERCENARIES2_RING_WRITEBACK=$([int]$RingWriteback.IsPresent)"
$perfOptions += " -DMERCENARIES2_NATIVE_TABLE_LOOKUP=$([int]$NativeTableLookup.IsPresent) -DMERCENARIES2_LOOKUP_FRAME_CSV=$([int]$LookupFrameCsv.IsPresent)"
$pgoOptions = "-DMERCENARIES2_PGO=$Pgo -DMERCENARIES2_PGO_SKIP_TEXTURES=$([int]$PgoSkipTextures.IsPresent) -DMERCENARIES2_PGO_SKIP_NATIVE_SYSTEM=$([int]$PgoSkipNativeSystem.IsPresent) -DMERCENARIES2_PGO_SKIP_RENDERER=$([int]$PgoSkipRenderer.IsPresent)"
if ($Pgo -ne 'OFF') { $pgoOptions += " -DMERCENARIES2_PGO_DEVICE_DIR=sdmc:/switch/Mercenaries2/pgo/$PgoSession -DMERCENARIES2_PGO_DATA=/work/out/pgo-data/$PgoDataSession" }
& docker run --rm --mount "type=bind,source=$projectRoot,target=/work" -w /work $Image bash -lc "cmake -S app -B $BuildDirectory -G Ninja -DCMAKE_BUILD_TYPE=Release -DCMAKE_EXPORT_COMPILE_COMMANDS=ON -DCMAKE_TOOLCHAIN_FILE=/work/tools/switch/cmake/switch-devkitA64.cmake -DREXSDK_DIR=/work/reference/masseffect-nx/sdk -DREXGLUE_SWITCH_NVK_SDK=/work/out/mesa-sdk/opt/devkitpro/portlibs/switch -DMERCENARIES2_EMULATOR_GUARDS=OFF $pgoOptions $perfOptions && cmake --build $BuildDirectory --target mercenaries2 -j $Jobs"
if ($LASTEXITCODE) { throw 'Switch build failed' }
