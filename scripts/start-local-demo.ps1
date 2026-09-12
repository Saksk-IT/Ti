[CmdletBinding()]
param(
    [ValidateRange(1, 65535)][int]$Port = 8000,
    [ValidateRange(1, 65535)][int]$PostgresPort = 55432
)

$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path $PSScriptRoot -Parent
$restoredEnvFile = Join-Path $projectRoot '.env.local-restored'
$usingRestoredData = Test-Path -LiteralPath $restoredEnvFile
$environmentFile = if ($usingRestoredData) { $restoredEnvFile } else { Join-Path $projectRoot 'local-demo.env.example' }
$compose = @('--env-file', $environmentFile,
    '-f', (Join-Path $projectRoot 'compose.dev.yml'),
    '-f', (Join-Path $projectRoot 'compose.local.yml'))
$previousPort = $env:WEB_PORT
$previousPostgresPort = $env:POSTGRES_PORT

function Invoke-DemoCompose {
    & docker compose @compose @args
    if ($LASTEXITCODE -ne 0) { throw "Docker Compose failed: $args" }
}

try {
    $env:WEB_PORT = "$Port"
    $env:POSTGRES_PORT = "$PostgresPort"
    & docker info --format '{{.ServerVersion}}'
    if ($LASTEXITCODE -ne 0) {
        throw 'Docker engine is unavailable. Start Docker Desktop with WSL 2, then retry.'
    }
    Invoke-DemoCompose config --quiet
    Invoke-DemoCompose build web
    Invoke-DemoCompose up -d --wait postgres redis
    Invoke-DemoCompose run --rm --no-deps web flask db upgrade
    if (-not $usingRestoredData) {
        $seedScript = Get-ChildItem $PSScriptRoot -Filter '*.py' | Where-Object {
            Select-String -LiteralPath $_.FullName -Pattern '^def _run_reset_and_seed\(' -Quiet
        } | Select-Object -First 1
        if (-not $seedScript) { throw 'Demo seed script was not found.' }
        Invoke-DemoCompose run --rm --no-deps web python "/app/scripts/$($seedScript.Name)" --empty-only
    }
    Invoke-DemoCompose up -d --wait --wait-timeout 180
    $baseUrl = "http://localhost:$Port"
    if ($usingRestoredData) {
        $health = Invoke-RestMethod "$baseUrl/api/ping?deep=1"
        if (-not $health.data.db -or -not $health.data.redis) { throw 'Restored data health verification failed.' }
        Write-Host "Restored local environment ready: $baseUrl"
        Write-Host 'Sign in with the original production account and password.'
    } else {
        $login = Invoke-RestMethod "$baseUrl/api/login" -Method Post -ContentType 'application/json' -Body (
            @{ username = 'admin@example.dev'; password = 'DevPass123!' } | ConvertTo-Json
        )
        if ($login.status -ne 'success') { throw 'Administrator login verification failed.' }
        Write-Host "Demo ready: $baseUrl"
        Write-Host 'Administrator: admin@example.dev / DevPass123!'
        Write-Host 'Student: student_a@example.dev / DevPass123!'
    }
} finally {
    $env:WEB_PORT = $previousPort
    $env:POSTGRES_PORT = $previousPostgresPort
}
