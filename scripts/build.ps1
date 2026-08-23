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
$env:LOCALSCRIBE_DIAGNOSTIC = "1"
$SmokeProcess = Start-Process -FilePath $Executable -PassThru -WindowStyle Hidden
Start-Sleep -Seconds 4
if ($SmokeProcess.HasExited) { throw "Packaged application failed its startup smoke test" }
Stop-Process -Id $SmokeProcess.Id
Remove-Item Env:\LOCALSCRIBE_DIAGNOSTIC
$Version = & $PythonExecutable -c "import sys; sys.path.insert(0, 'src'); import localscribe; print(localscribe.__version__)"
$ReleaseDirectory = Join-Path $ProjectRoot "release"
New-Item -ItemType Directory -Force $ReleaseDirectory | Out-Null
$Archive = Join-Path $ReleaseDirectory "LocalScribe-Flow-$Version-windows-x64.zip"
Compress-Archive -Path "dist/LocalScribe Flow/*" -DestinationPath $Archive -Force
Get-FileHash $Archive -Algorithm SHA256 | ForEach-Object { "$($_.Hash.ToLower())  $(Split-Path -Leaf $Archive)" } |
    Set-Content -Encoding ascii "$Archive.sha256"
Write-Host "Built $Archive"
