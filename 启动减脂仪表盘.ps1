$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$port = 8765
$url = "http://127.0.0.1:$port/"
$apiUrl = "http://127.0.0.1:$port/api/dashboard"
$serverLog = Join-Path $root 'dashboard-server.log'
$serverErrorLog = Join-Path $root 'dashboard-server-error.log'

function Open-Dashboard {
    Start-Process -FilePath 'explorer.exe' -ArgumentList $url
}

try {
    Invoke-WebRequest -UseBasicParsing $apiUrl -TimeoutSec 2 | Out-Null
    Open-Dashboard
    Write-Output "Dashboard already running: $url"
    exit 0
} catch {}

$python = $null
$prefixArgs = @()
if (Get-Command py.exe -ErrorAction SilentlyContinue) {
    $python = (Get-Command py.exe).Source
    $prefixArgs = @('-3')
} elseif (Get-Command python.exe -ErrorAction SilentlyContinue) {
    $python = (Get-Command python.exe).Source
} else {
    throw 'Windows Python was not found. Install Python 3.11 or newer and enable the Python launcher.'
}

Remove-Item $serverLog -ErrorAction SilentlyContinue
Remove-Item $serverErrorLog -ErrorAction SilentlyContinue
$arguments = $prefixArgs + @('backend\server.py', '--port', "$port")
$process = Start-Process -FilePath $python -ArgumentList $arguments -WorkingDirectory $root -WindowStyle Hidden -RedirectStandardOutput $serverLog -RedirectStandardError $serverErrorLog -PassThru

$ready = $false
for ($i = 0; $i -lt 60; $i++) {
    if ($process.HasExited) { break }
    try {
        Invoke-WebRequest -UseBasicParsing $apiUrl -TimeoutSec 1 | Out-Null
        $ready = $true
        break
    } catch {
        Start-Sleep -Milliseconds 250
    }
}

if (-not $ready) {
    $output = if (Test-Path $serverLog) { Get-Content $serverLog -Raw } else { '' }
    $errors = if (Test-Path $serverErrorLog) { Get-Content $serverErrorLog -Raw } else { '' }
    $detail = ($output + "`n" + $errors).Trim()
    if (-not $detail) { $detail = 'No server log was created.' }
    throw "Dashboard failed to start. $detail"
}

Open-Dashboard
Write-Output "Dashboard started: $url"
