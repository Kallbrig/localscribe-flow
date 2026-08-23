param(
    [switch]$SkipInstall
)
$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot
$VenvPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$PythonExecutable = if (Test-Path $VenvPython) { $VenvPython } else { "python" }
if (-not $SkipInstall) {
    & $PythonExecutable -m pip install --upgrade pip
    & $PythonExecutable -m pip install ".[app,dev]"
    & $PythonExecutable -m pip install llama-cpp-python --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cpu
}
& $PythonExecutable -m pytest
if ($LASTEXITCODE -ne 0) { throw "Tests failed" }
& $PythonExecutable -m PyInstaller packaging/LocalScribeFlow.spec --noconfirm --clean
if ($LASTEXITCODE -ne 0) { throw "PyInstaller build failed" }
$Executable = Join-Path $ProjectRoot "dist\LocalScribe Flow\LocalScribe Flow.exe"
$DiagnosticMarker = Join-Path $ProjectRoot "build\package-smoke.ok"
Remove-Item -LiteralPath $DiagnosticMarker -Force -ErrorAction SilentlyContinue
$env:LOCALSCRIBE_DIAGNOSTIC = "1"
$env:LOCALSCRIBE_DIAGNOSTIC_FILE = $DiagnosticMarker
try {
    $SmokeProcess = Start-Process -FilePath $Executable -PassThru -WindowStyle Hidden
    if (-not $SmokeProcess.WaitForExit(15000)) {
        Stop-Process -Id $SmokeProcess.Id -Force
        throw "Packaged application did not finish its diagnostic startup check"
    }
    if ($SmokeProcess.ExitCode -ne 0 -or -not (Test-Path -LiteralPath $DiagnosticMarker)) {
        throw "Packaged application failed its diagnostic startup check"
    }
}
finally {
    Remove-Item Env:\LOCALSCRIBE_DIAGNOSTIC -ErrorAction SilentlyContinue
    Remove-Item Env:\LOCALSCRIBE_DIAGNOSTIC_FILE -ErrorAction SilentlyContinue
}
$Version = & $PythonExecutable -c "import sys; sys.path.insert(0, 'src'); import localscribe; print(localscribe.__version__)"
$ReleaseDirectory = Join-Path $ProjectRoot "release"
New-Item -ItemType Directory -Force $ReleaseDirectory | Out-Null
$Archive = Join-Path $ReleaseDirectory "LocalScribe-Flow-$Version-windows-x64.zip"
Compress-Archive -Path "dist/LocalScribe Flow/*" -DestinationPath $Archive -Force
Get-FileHash $Archive -Algorithm SHA256 | ForEach-Object { "$($_.Hash.ToLower())  $(Split-Path -Leaf $Archive)" } |
    Set-Content -Encoding ascii "$Archive.sha256"
Write-Host "Built $Archive"
