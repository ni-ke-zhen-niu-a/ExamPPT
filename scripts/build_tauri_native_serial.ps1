$ErrorActionPreference='Stop'
$env:CARGO_HOME='D:\Tools\rust\cargo'
$env:RUSTUP_HOME='D:\Tools\rust\rustup'
$env:CARGO_BUILD_JOBS='1'
$rustBin='D:\Tools\rust\rustup\toolchains\stable-x86_64-pc-windows-msvc\bin'
$env:Path="$rustBin;$env:Path"
cmd /c "call D:\Tools\VSBuildTools\VC\Auxiliary\Build\vcvars64.bat && cd /d D:\Projects\ExamPPT\app\desktop && npm run tauri build"
exit $LASTEXITCODE
