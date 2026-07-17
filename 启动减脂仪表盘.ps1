$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$port = 8765
$url = "http://127.0.0.1:$port"

try {
    Invoke-WebRequest -UseBasicParsing "$url/api/dashboard" -TimeoutSec 2 | Out-Null
    Start-Process $url
    exit 0
} catch {}

$python = $null
$arguments = @()
if (Get-Command py.exe -ErrorAction SilentlyContinue) {
    $python = 'py.exe'
    $arguments = @('-3')
} elseif (Get-Command python.exe -ErrorAction SilentlyContinue) {
    $python = 'python.exe'
} else {
    Add-Type -AssemblyName PresentationFramework
    [System.Windows.MessageBox]::Show('Windows Python was not found. Install Python 3.11 or newer.','Fat Loss Dashboard') | Out-Null
    exit 1
}

$arguments += @('backend\server.py', '--port', $port)
Start-Process -FilePath $python -ArgumentList $arguments -WorkingDirectory $root -WindowStyle Minimized

$ready = $false
for ($i = 0; $i -lt 40; $i++) {
    try {
        Invoke-WebRequest -UseBasicParsing "$url/api/dashboard" -TimeoutSec 1 | Out-Null
        $ready = $true
        break
    } catch {
        Start-Sleep -Milliseconds 250
    }
}
if (-not $ready) {
    Add-Type -AssemblyName PresentationFramework
    [System.Windows.MessageBox]::Show('Dashboard failed to start. Check whether port 8765 is occupied.','Fat Loss Dashboard') | Out-Null
    exit 1
}
Start-Process $url
