$connections = Get-NetTCPConnection -LocalAddress 127.0.0.1 -LocalPort 8765 -State Listen -ErrorAction SilentlyContinue
if (-not $connections) { exit 0 }
foreach ($processId in ($connections | Select-Object -ExpandProperty OwningProcess -Unique)) {
    $process = Get-CimInstance Win32_Process -Filter "ProcessId=$processId" -ErrorAction SilentlyContinue
    if ($process -and $process.CommandLine -match 'server\.py' -and $process.CommandLine -match '8765') {
        Stop-Process -Id $processId -Force
    } else {
        Add-Type -AssemblyName PresentationFramework
        [System.Windows.MessageBox]::Show("Port 8765 belongs to another process. PID $processId was not stopped.",'Fat Loss Dashboard') | Out-Null
        exit 1
    }
}
