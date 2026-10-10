param([string]$ReXGlue = "")
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
if (-not $ReXGlue) {
    $candidate = Get-ChildItem -LiteralPath (Join-Path $PSScriptRoot 'bin') -Filter rexglue.exe -Recurse | Select-Object -First 1
    if (-not $candidate) { throw 'ReXGlue not found. Extract the official Windows SDK under tools/bin.' }
    $ReXGlue = $candidate.FullName
}
New-Item -ItemType Directory -Force (Join-Path $projectRoot 'out') | Out-Null
$gameXex = Join-Path $projectRoot 'assets/game_root/default.xex'
$expectedHash = '48e805e4a2c1c4f7b409245dc9f2d02e2e8a94eaa0e9f1744d150ddce00bf72b'
if ((Get-FileHash -LiteralPath $gameXex -Algorithm SHA256).Hash.ToLowerInvariant() -ne $expectedHash) {
    throw 'This manifest only supports the inspected Mercenaries 2 edition. XEX SHA-256 differs.'
}
Push-Location $projectRoot
try {
    & $ReXGlue --log-file out/codegen.log codegen app/mercenaries2_manifest.toml
    if ($LASTEXITCODE -ne 0) { throw "Code generation failed ($LASTEXITCODE). See out/codegen.log." }
    python (Join-Path $PSScriptRoot 'prepare_switch_codegen.py')
    if ($LASTEXITCODE) { throw 'GCC header preparation failed' }
} finally { Pop-Location }
