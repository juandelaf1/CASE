# CASE API — Start in background
# Usage: .\scripts\start_api.ps1

$port = 8000
$host = "127.0.0.1"
$healthUrl = "http://${host}:${port}/health"
$logFile = Join-Path $PSScriptRoot "..\api.log"

# Stop existing process on port
$existing = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue |
    Select-Object -ExpandProperty OwningProcess -Unique
if ($existing) {
    foreach ($pid in $existing) {
        $proc = Get-Process -Id $pid -ErrorAction SilentlyContinue
        if ($proc -and $proc.ProcessName -eq "uvicorn") {
            Write-Host "Stopping existing uvicorn (PID $pid)..."
            Stop-Process -Id $pid -Force
            Start-Sleep -Seconds 2
        }
    }
}

# Start API in background
Write-Host "Starting CASE API on ${host}:${port}..."
$process = Start-Process -FilePath "uvicorn" `
    -ArgumentList "case_api.api.v1.app:app","--host",$host,"--port",$port `
    -NoNewWindow -PassThru -RedirectStandardOutput $logFile -RedirectStandardError "$logFile.err"

# Wait for health
Write-Host "Waiting for API..."
$maxWait = 15
for ($i = 0; $i -lt $maxWait; $i++) {
    Start-Sleep -Seconds 1
    try {
        $response = Invoke-WebRequest -Uri $healthUrl -TimeoutSec 2 -UseBasicParsing -ErrorAction Stop
        $body = $response.Content | ConvertFrom-Json
        if ($body.status -eq "ok" -or $body.status -eq "degraded") {
            Write-Host "API ready (PID $($process.Id), status: $($body.status))"
            Write-Host "Health: $healthUrl"
            Write-Host "Docs:   http://${host}:${port}/docs"
            Write-Host "Log:    $logFile"
            exit 0
        }
    } catch {
        # Not ready yet
    }
}

Write-Host "API failed to start within ${maxWait}s. Check $logFile"
exit 1
