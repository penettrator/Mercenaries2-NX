param([string]$Nro,[string]$Toml,[string]$Verify)
# Copies the given NRO and/or TOML to sdmc:/switch/Mercenaries2 and reads them back into $Verify.
$ErrorActionPreference='Stop'
$root='D:\Mercenaries2-switch'
$s=New-Object -ComObject Shell.Application
$sw=$s.Namespace(17).Items() | ? { $_.Name -eq 'Switch' }
$sd=$sw.GetFolder.Items() | ? { $_.Name -eq '1: SD Card' }
$m=($sd.GetFolder.Items() | ? { $_.Name -eq 'switch' }).GetFolder.Items() | ? { $_.Name -eq 'Mercenaries2' }
$names=@()
if($Nro){ & "$root\tools\copy_mtp_nro.ps1" -Source $Nro -DestinationShellItem $m; $names+='mercenaries2.nro' }
if($Toml){ & "$root\tools\copy_mtp_toml.ps1" -Source $Toml -DestinationShellItem $m; $names+='mercenaries2.toml' }
New-Item -ItemType Directory -Force $Verify | Out-Null
foreach($n in $names){ Remove-Item "$Verify\$n" -Force -ErrorAction SilentlyContinue; $it=$m.GetFolder.Items() | ? { $_.Name -eq $n }; $s.Namespace($Verify).CopyHere($it,4+16+1024) }
$d=(Get-Date).AddMinutes(5)
foreach($n in $names){ $src= if($n -like '*.nro'){$Nro}else{$Toml}; while(((-not (Test-Path "$Verify\$n")) -or (Get-Item "$Verify\$n").Length -lt (Get-Item $src).Length) -and (Get-Date) -lt $d){ Start-Sleep 2 } }
Start-Sleep 2
foreach($n in $names){ "$n " + (Get-FileHash "$Verify\$n").Hash.ToLower() }
