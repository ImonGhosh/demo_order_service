param(
    [string]$EnvPath = "$PSScriptRoot\.env",
    [string]$ConfigPath = "$PSScriptRoot\demo-order-service.alloy",
    [string]$AlloyExecutable = "alloy-windows-amd64.exe",
    [string]$StoragePath = "$PSScriptRoot\..\..\data-alloy",
    [string]$ListenAddr = "127.0.0.1:12345",
    [switch]$CheckOnly
)

$ErrorActionPreference = "Stop"

$requiredVariables = @(
    "GRAFANA_LOKI_URL",
    "GRAFANA_LOKI_USERNAME",
    "GRAFANA_LOKI_TOKEN",
    "DEMO_ORDER_SERVICE_LOG_PATH"
)

function Import-DotEnv {
    param([string]$Path)

    if (-not (Test-Path -LiteralPath $Path)) {
        throw "Missing Alloy .env file: $Path. Create it from observability/alloy/.env.example."
    }

    Get-Content -LiteralPath $Path | ForEach-Object {
        $line = $_.Trim()
        if (-not $line -or $line.StartsWith("#")) {
            return
        }

        if ($line.StartsWith("export ")) {
            $line = $line.Substring(7).Trim()
        }

        $parts = $line -split "=", 2
        if ($parts.Count -ne 2) {
            return
        }

        $name = $parts[0].Trim()
        $value = $parts[1].Trim()

        if (
            ($value.StartsWith('"') -and $value.EndsWith('"')) -or
            ($value.StartsWith("'") -and $value.EndsWith("'"))
        ) {
            $value = $value.Substring(1, $value.Length - 2)
        }

        if ($name) {
            Set-Item -Path "Env:$name" -Value $value
        }
    }
}

function Assert-RequiredVariables {
    foreach ($name in $requiredVariables) {
        $value = [Environment]::GetEnvironmentVariable($name)
        if ([string]::IsNullOrWhiteSpace($value)) {
            throw "Missing required environment variable: $name"
        }
    }
}

Import-DotEnv -Path $EnvPath
Assert-RequiredVariables

Write-Host "Loaded Alloy environment from $EnvPath"
foreach ($name in $requiredVariables) {
    $value = [Environment]::GetEnvironmentVariable($name)
    Write-Host "$name=loaded ($($value.Length) chars)"
}

if ($CheckOnly) {
    Write-Host "Check complete. Alloy was not started."
    exit 0
}

Write-Host "Starting Alloy with config $ConfigPath"
& $AlloyExecutable run `
    "--server.http.listen-addr=$ListenAddr" `
    "--storage.path=$StoragePath" `
    $ConfigPath
