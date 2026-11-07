# Run every check on Windows PowerShell (same steps as check.sh). Offline after install; no provider calls, no API key.
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot

function Invoke-Step([string]$Dir, [string]$Tool, [string[]]$CmdArgs) {
    Push-Location $Dir
    try {
        & $Tool @CmdArgs
        if ($LASTEXITCODE -ne 0) { throw "failed: $Tool $($CmdArgs -join ' ')" }
    } finally { Pop-Location }
}

Write-Host "== secret scan"
Invoke-Step $Root "uv" @("run", "--no-sync", "--project", "backend", "python", "scripts\check_secrets.py")

Write-Host "== backend"
$Backend = Join-Path $Root "backend"
Invoke-Step $Backend "uv" @("run", "--no-sync", "ruff", "check", ".", "..\scripts")
Invoke-Step $Backend "uv" @("run", "--no-sync", "ruff", "format", "--check", ".", "..\scripts")
Invoke-Step $Backend "uv" @("run", "--no-sync", "mypy")
Invoke-Step $Backend "uv" @("run", "--no-sync", "pytest", "-q")
Invoke-Step $Backend "uv" @("run", "--no-sync", "python", "-m", "app.smoke")

Write-Host "== frontend"
Invoke-Step (Join-Path $Root "frontend") "npm.cmd" @("run", "--silent", "check")

Write-Host "== end-to-end smoke (real backend + UI, temporary data dir)"
Invoke-Step $Root "uv" @("run", "--no-sync", "--project", "backend", "python", "scripts\e2e_smoke.py")

Write-Host "ALL CHECKS PASSED"
