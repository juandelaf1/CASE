# CASE API — Stop
# Usage: .\scripts\stop_api.ps1

$port = 8000

$existing = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue |
    Select-Object -ExpandProperty OwningProcess -Unique

if (-not $existing) {
    Write-Host "No API process found on port $port."
    exit 0
}

foreach ($pid in $existing) {
    $proc = Get-Process -Id $pid -ErrorAction SilentlyContinue
    if ($proc -and $proc.ProcessName -eq "uvicorn") {
        Write-Host "Stopping uvicorn (PID $pid)..."
        Stop-Process -Id $pid -Force
    }
}

Write-Host "API stopped."
