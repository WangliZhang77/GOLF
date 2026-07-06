# NZ Golf CRM - one-click start (Windows PowerShell)
# Usage:
#   .\scripts\start.ps1
#   .\scripts\start.ps1 -SkipSeed
#   .\scripts\start.ps1 -SkipInstall

param(
    [switch]$SkipSeed,
    [switch]$SkipInstall
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$Backend = Join-Path $Root "backend"
$AdminWeb = Join-Path $Root "admin-web"
$MemberWeb = Join-Path $Root "member-web"
$VenvPython = Join-Path $Backend ".venv\Scripts\python.exe"
$VenvPip = Join-Path $Backend ".venv\Scripts\pip.exe"

function Write-Step([string]$msg) {
    Write-Host ""
    Write-Host "==> $msg" -ForegroundColor Cyan
}

function Test-PortInUse([int]$Port) {
    $conn = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
    return $null -ne $conn
}

Set-Location $Root

Write-Host ""
Write-Host "  NZ Golf CRM - starting..." -ForegroundColor Green
Write-Host "  Root: $Root" -ForegroundColor Green
Write-Host ""

# --- Docker ---
Write-Step "Starting PostgreSQL (docker compose)"
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Host "Docker not found. Please install and start Docker Desktop." -ForegroundColor Red
    exit 1
}
docker compose up -d db
if ($LASTEXITCODE -ne 0) {
    Write-Host "docker compose failed. Is Docker Desktop running?" -ForegroundColor Red
    exit 1
}

Write-Step "Waiting for database"
$retries = 30
$ready = $false
for ($i = 1; $i -le $retries; $i++) {
    docker compose exec -T db pg_isready -U golf -d golf_crm 2>$null | Out-Null
    if ($LASTEXITCODE -eq 0) {
        $ready = $true
        break
    }
    Start-Sleep -Seconds 1
}
if (-not $ready) {
    Write-Host "Database not ready within ${retries}s. Check: docker compose logs db" -ForegroundColor Red
    exit 1
}

# --- Backend ---
Write-Step "Preparing Python venv"
if (-not (Test-Path $VenvPython)) {
    python -m venv (Join-Path $Backend ".venv")
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Failed to create venv. Need Python 3.12+." -ForegroundColor Red
        exit 1
    }
}

$envFile = Join-Path $Backend ".env"
$envExample = Join-Path $Backend ".env.example"
if (-not (Test-Path $envFile) -and (Test-Path $envExample)) {
    Copy-Item $envExample $envFile
    Write-Host "Copied backend\.env.example -> .env"
}

if (-not $SkipInstall) {
    & $VenvPip install -q -r (Join-Path $Backend "requirements.txt")
}

Write-Step "Running alembic migrations"
Set-Location $Backend
& $VenvPython -m alembic upgrade head
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

if (-not $SkipSeed) {
    Write-Step "Seeding demo data"
    & $VenvPython -m app.seed
}

Set-Location $Root

foreach ($p in @(8000, 5173, 5174)) {
    if (Test-PortInUse $p) {
        Write-Host "Warning: port $p is already in use." -ForegroundColor Yellow
    }
}

# --- Start services in new windows ---
Write-Step "Starting backend API (http://localhost:8000)"
$backendCmd = "Set-Location '$Backend'; Write-Host 'Backend API - Ctrl+C to stop' -ForegroundColor Green; & '$VenvPython' -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000"
Start-Process powershell -ArgumentList "-NoExit", "-Command", $backendCmd

if (-not $SkipInstall) {
    if (-not (Test-Path (Join-Path $AdminWeb "node_modules"))) {
        Write-Step "npm install admin-web"
        Set-Location $AdminWeb
        npm install --silent
        Set-Location $Root
    }
    if (-not (Test-Path (Join-Path $MemberWeb "node_modules"))) {
        Write-Step "npm install member-web"
        Set-Location $MemberWeb
        npm install --silent
        Set-Location $Root
    }
}

Write-Step "Starting admin-web (http://localhost:5173)"
$adminCmd = "Set-Location '$AdminWeb'; Write-Host 'Admin web - Ctrl+C to stop' -ForegroundColor Green; npm run dev"
Start-Process powershell -ArgumentList "-NoExit", "-Command", $adminCmd

Write-Step "Starting member-web (http://localhost:5174)"
$memberCmd = "Set-Location '$MemberWeb'; Write-Host 'Member web - Ctrl+C to stop' -ForegroundColor Green; npm run dev"
Start-Process powershell -ArgumentList "-NoExit", "-Command", $memberCmd

Write-Host ""
Write-Host "  Done!" -ForegroundColor Green
Write-Host "  Admin:  http://localhost:5173   admin / admin123456" -ForegroundColor Green
Write-Host "  Member: http://localhost:5174   demo  / demo123456" -ForegroundColor Green
Write-Host "  API:    http://localhost:8000/docs" -ForegroundColor Green
Write-Host "  Guide:  docs\演示走查.md" -ForegroundColor Green
Write-Host "  Stop:   .\scripts\stop.ps1" -ForegroundColor Green
Write-Host ""
