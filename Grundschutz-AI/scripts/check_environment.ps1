# Read-only environment check for Sprint 0. Does not install or modify anything.
$ErrorActionPreference = 'Continue'
Write-Host '=== Grundschutz AI / Sprint 0 environment report ==='
Write-Host "Date: $(Get-Date -Format s)"
Write-Host "Windows: $([Environment]::OSVersion.VersionString)"
Write-Host "RAM (GB): $([math]::Round((Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory / 1GB, 1))"
$cpu = Get-CimInstance Win32_Processor | Select-Object -First 1 -ExpandProperty Name
Write-Host "CPU: $cpu"
$gpus = Get-CimInstance Win32_VideoController | Select-Object -ExpandProperty Name
Write-Host "GPU(s): $($gpus -join ', ')"
foreach ($tool in @('git', 'code', 'py', 'winget')) {
  $cmd = Get-Command $tool -ErrorAction SilentlyContinue
  if ($cmd) { Write-Host "[OK] $tool => $($cmd.Source)" } else { Write-Host "[MISSING] $tool" }
}
try { Write-Host "Python 3.12: $(& py -3.12 --version 2>&1)" } catch { Write-Host '[MISSING] Python 3.12' }
try { $space = Get-PSDrive -Name C; Write-Host "Free space on C: $([math]::Round($space.Free / 1GB, 1)) GB" } catch {}
Write-Host 'This script does not test or send any company documents.'
