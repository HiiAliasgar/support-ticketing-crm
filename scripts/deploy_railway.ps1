# Deploys the repo to Railway and prints the public URL.
#
# Requirements: a Railway account token from
#   https://railway.com/account/tokens  (create, then copy)
#
# Usage:
#   $env:RAILWAY_TOKEN="<your token>"
#   .\scripts\deploy_railway.ps1
#
# What it does:
#   1. downloads the Railway CLI (portable, into .tools/)
#   2. logs in with your token
#   3. creates project "support-ticketing-crm"
#   4. uploads this directory and builds it (Dockerfile) in the cloud
#   5. provisions a public railway.app domain

$ErrorActionPreference = "Stop"

if (-not $env:RAILWAY_TOKEN) {
    throw "Set RAILWAY_TOKEN first: https://railway.com/account/tokens"
}

$root = Split-Path -Parent $PSScriptRoot
$tools = Join-Path $root ".tools"
$cliDir = Join-Path $tools "railway"
New-Item -ItemType Directory -Force -Path $cliDir | Out-Null

# --- 1. Download PortableRailway CLI ---------------------------------------
$exe = Join-Path $cliDir "railway.exe"
if (-not (Test-Path $exe)) {
    Write-Host "[1/4] Downloading Railway CLI..."
    $release = Invoke-RestMethod -Uri "https://api.github.com/repos/railwayapp/cli/releases/latest" -Headers @{"User-Agent" = "supporttick"}
    $zipAsset = $release.assets | Where-Object { $_.name -like "*.zip" -and $_.name -match "x86_64-pc-windows-msvc" } | Select-Object -First 1
    if (-not $zipAsset) { throw "Could not find a Windows ZIP asset in Railway CLI release" }
    $zipPath = Join-Path $cliDir "railway.zip"
    Invoke-WebRequest -Uri $zipAsset.browser_download_url -OutFile $zipPath
    Expand-Archive -Path $zipPath -DestinationPath $cliDir -Force
    if (-not (Test-Path $exe)) {
        $exe = (Get-ChildItem $cliDir -Filter railway.exe -Recurse | Select-Object -First 1).FullName
    }
}

# --- 2. Auth check (the CLI authenticates purely via RAILWAY_TOKEN) ---------
Write-Host "[2/4] Verifying token... (use a fresh 'Account token' from https://railway.com/account/tokens)"
& $exe list | Out-Host
if ($LASTEXITCODE -ne 0) {
    throw "Authentication failed. If the token was shown once before, it is revoked - generate a NEW one at https://railway.com/account/tokens with all scopes and no expiry, then rerun."
}

# --- 3. Project --------------------------------------------------------------
Write-Host "[3/4] Creating project..."
Push-Location $root
try {
    & $exe init --name support-ticketing-crm | Out-Host
    if ($LASTEXITCODE -ne 0) { throw "railway init failed" }

    # --- 4. Deploy (builds the Dockerfile in the cloud) ---
    Write-Host "[4/4] Deploying (detached) - this builds the Docker image in the cloud..."
    & $exe up --detach | Out-Host
    if ($LASTEXITCODE -ne 0) { throw "railway up failed" }

    Write-Host "Provisioning a public domain..."
    & $exe domain | Out-Host
    Write-Host ""
    Write-Host "Deploy started. Watch it at:"
    & $exe logs --deployment | Out-Host
} finally {
    Pop-Location
}