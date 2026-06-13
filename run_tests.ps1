$ErrorActionPreference = "Continue"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = if ($env:PYTHON) { $env:PYTHON } else { "python" }
$LogDir = Join-Path $Root "test-artifacts\logs"
$CoverageDir = Join-Path $Root "test-artifacts\coverage"

New-Item -ItemType Directory -Force -Path $LogDir, $CoverageDir | Out-Null

$Timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$BackendLog = Join-Path $LogDir "backend-$Timestamp.log"
$FrontendLog = Join-Path $LogDir "frontend-$Timestamp.log"
$BuildLog = Join-Path $LogDir "frontend-build-$Timestamp.log"

Push-Location (Join-Path $Root "backend")
& $Python -m pytest --cov=app --cov-report=term-missing --cov-report="html:$CoverageDir" 2>&1 |
    Tee-Object -FilePath $BackendLog
$BackendExit = $LASTEXITCODE
Pop-Location

Push-Location (Join-Path $Root "frontend")
& npm test 2>&1 | Tee-Object -FilePath $FrontendLog
$FrontendExit = $LASTEXITCODE
& npm run build 2>&1 | Tee-Object -FilePath $BuildLog
$BuildExit = $LASTEXITCODE
Pop-Location

Write-Host "Backend log: $BackendLog"
Write-Host "Frontend log: $FrontendLog"
Write-Host "Build log: $BuildLog"

if (($BackendExit -ne 0) -or ($FrontendExit -ne 0) -or ($BuildExit -ne 0)) {
    exit 1
}
