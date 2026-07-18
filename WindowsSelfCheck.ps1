$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$port = 8765
$apiUrl = "http://127.0.0.1:$port/api/dashboard"
$failed = $false

function Report-Check {
    param(
        [bool]$Passed,
        [string]$Name,
        [string]$Detail
    )
    $status = if ($Passed) { 'PASS' } else { 'FAIL' }
    Write-Output "[$status] $Name - $Detail"
    if (-not $Passed) { $script:failed = $true }
}

Write-Output 'Fat-loss tracker Windows self-check'

$python = $null
$pythonArgs = @()
if (Get-Command py.exe -ErrorAction SilentlyContinue) {
    $python = (Get-Command py.exe).Source
    $pythonArgs = @('-3')
} elseif (Get-Command python.exe -ErrorAction SilentlyContinue) {
    $python = (Get-Command python.exe).Source
} else {
    Report-Check $false 'Python' 'Python 3.11 or newer was not found.'
}

if ($python) {
    try {
        $version = & $python @pythonArgs -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
        $parts = $version.Trim().Split('.')
        $supported = [int]$parts[0] -eq 3 -and [int]$parts[1] -ge 11
        Report-Check $supported 'Python' "Detected Python $($version.Trim())."
    } catch {
        Report-Check $false 'Python' 'Python could not be executed.'
    }
}

try {
    $probe = Join-Path $root '.write-probe.tmp'
    [System.IO.File]::WriteAllText($probe, 'ok', [System.Text.Encoding]::ASCII)
    Remove-Item $probe -Force
    Report-Check $true 'Project write access' 'Project directory is writable.'
} catch {
    Report-Check $false 'Project write access' 'Project directory is not writable.'
}

$connections = Get-NetTCPConnection -LocalAddress 127.0.0.1 -LocalPort $port -State Listen -ErrorAction SilentlyContinue
if ($connections) {
    try {
        $response = Invoke-WebRequest -UseBasicParsing $apiUrl -TimeoutSec 2
        Report-Check ($response.StatusCode -eq 200) 'Dashboard health' "Running service returned HTTP $($response.StatusCode)."
    } catch {
        Report-Check $false 'Dashboard health' 'Port 8765 is listening but the dashboard health endpoint is unavailable.'
    }
} else {
    Report-Check $true 'Dashboard health' 'No dashboard is running; start it with the dashboard launcher when needed.'
}

$profile = Join-Path $root 'profile.json'
$config = Join-Path $root 'config.json'
if (Test-Path $profile) {
    Report-Check $true 'Private profile' 'profile.json exists locally and must remain Git-ignored.'
} elseif (Test-Path $config) {
    Report-Check $true 'Legacy private config' 'config.json exists locally; first-launch migration will preserve eligible settings.'
} else {
    Report-Check $true 'Private profile' 'No local profile yet; first-launch setup will create one.'
}

if ($failed) {
    exit 1
}
exit 0
