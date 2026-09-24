# Deploys the repo to Railway and prints the public URL.
#
# Two supported flows (the exact one used to bring this app live):
#
#   A) AWORKSPACE/account token + one-time bootstrap:
#       1. Create project + a project token via the Railway GraphQL API
#          (see the bootstrap steps used in README/production notes).
#       2. Paste the PROJECT token here.
#
#   B) PROJECT token (recommended for redeploys):
#       $env:RAILWAY_TOKEN="<project-token>"
#       .\scripts\deploy_railway.ps1 -Service <service-id>
#
# Before running anywhere: API token vs project token confusion is real.
#   - RAILWAY_TOKEN        = project token (used by `railway up`)
#   - RAILWAY_API_TOKEN    = account/workspace token (GraphQL API / `railway api`)
#
# What this script does:
#   1. downloads the Railway CLI (portable, into .tools/)
#   2. verifies the token via `railway service list`
#   3. `railway up --detach --yes` uploads this directory and builds it
#      (Dockerfile) in the cloud, deploying to the --Service or the linked one
#   4. provisions a public railway.app domain (if missing)

param(
    [string]$Service
)

$ErrorActionPreference = "Stop"

if (-not $env:RAILWAY_TOKEN) {
    throw "Set RAILWAY_TOKEN to a Railway PROJECT token first."
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

# --- 2. Auth check -----------------------------------------------------------
Write-Host "[2/4] Verifying token..."
& $exe service list --json | Out-Host
if ($LASTEXITCODE -ne 0) {
    throw "Authentication failed. Use a PROJECT token (from project -> Settings -> Tokens), not an account token."
}

# --- 3. Deploy (uploads dir, builds Dockerfile in the cloud) -----------------
Push-Location $root
try {
    if ($Service) {
        Write-Host "[3/4] Deploying to service $Service (detached)..."
        & $exe up --detach --yes --service $Service | Out-Host
    } else {
        Write-Host "[3/4] Deploying (detached)..."
        & $exe up --detach --yes | Out-Host
    }
    if ($LASTEXITCODE -ne 0) { throw "railway up failed" }

    Write-Host "[4/4] Ensuring a public domain..."
    & $exe domain | Out-Host
    Write-Host ""
    Write-Host "Deployment started. Track it with:"
    Write-Host "  railway logs --deployment"
} finally {
    Pop-Location
}