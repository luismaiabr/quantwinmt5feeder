Write-Host "Starting QuantWin MT5 Live Scheduler..." -ForegroundColor Green
Write-Host "Initialises MT5, runs a startup backfill, and enters a 15-second polling loop."
Write-Host "Press Ctrl+C to stop."
Write-Host ""

$env:PYTHONPATH = "c:\Documents backup\QUANT\qDATA"
python -m poetry run python3 -m quantwinmt5feeder.scheduler

Write-Host ""
pause
