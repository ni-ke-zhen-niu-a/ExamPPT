$ErrorActionPreference='Stop'
$root=(Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$python=Join-Path $root '.venv\Scripts\python.exe'
if(-not (Test-Path $python)){
  $python=(Get-Command python).Source
}
$out=Join-Path $root 'build\sidecar'
$dist=Join-Path $root 'dist\sidecar'
$target=Join-Path $root 'app\desktop\src-tauri\binaries\examppt-core-x86_64-pc-windows-msvc.exe'
New-Item -ItemType Directory -Force -Path (Split-Path $target) | Out-Null
& $python -m PyInstaller --noconfirm --clean --onefile --console --name examppt-core --distpath $dist --workpath $out --specpath $out --collect-data examppt --collect-all pypdfium2 (Join-Path $root 'scripts\sidecar_entry.py')
Copy-Item -Force (Join-Path $dist 'examppt-core.exe') $target
Write-Host ('SIDECAR=' + $target)
& $target --version
