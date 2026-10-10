param([int]$WaitMinutes = 120)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $projectRoot
$deadline = (Get-Date).AddMinutes($WaitMinutes)
$statusPath = Join-Path $projectRoot 'out/switch-pipeline-status.json'
function Write-State([string]$stage, [string]$detail) {
    [ordered]@{stage=$stage; detail=$detail; updated=(Get-Date).ToString('o')} | ConvertTo-Json | Set-Content -LiteralPath $statusPath -Encoding utf8
    Write-Output "$stage : $detail"
}
try {
    Write-State 'waiting_for_toolchain' 'Waiting for mercenaries2-mesa-build:dev Docker image'
    while ($true) {
        & docker image inspect mercenaries2-mesa-build:dev --format '{{.Id}}' 2>$null | Out-Null
        if ($LASTEXITCODE -eq 0) { break }
        if ((Get-Date) -ge $deadline) { throw 'Toolchain image was not ready within the wait limit. Inspect out/mesa-image.log.' }
        Start-Sleep -Seconds 20
    }
    Write-State 'building_mesa' 'Compiling the Horizon NVK driver'
    & docker run --rm --mount "type=bind,source=$projectRoot,target=/work" --mount "type=bind,source=$projectRoot\reference\mesa-switch-src,target=/project" -w /project mercenaries2-mesa-build:dev bash /work/tools/build_mesa_inside.sh 2>&1 | Tee-Object -FilePath 'out/mesa-build.log'
    if ($LASTEXITCODE -ne 0) { throw "Mesa build failed (exit $LASTEXITCODE). Inspect out/mesa-build.log." }
    Write-State 'building_game' 'Compiling ReXGlue runtime and translated Mercenaries 2 code'
    & (Join-Path $PSScriptRoot 'build_switch.ps1') 2>&1 | Tee-Object -FilePath 'out/switch-build.log'
    $nro=Join-Path $projectRoot 'out/nx/mercenaries2.nro'
    if (-not (Test-Path -LiteralPath $nro)) { throw 'Build finished without the expected NRO' }
    Write-State 'built_unverified' 'NRO compiled; console launch and gameplay have not been tested'
} catch {
    Write-State 'failed' $_.Exception.Message
    throw
}
