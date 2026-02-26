Write-Host "Running QuantWin MT5 Manual Backfill Test..." -ForegroundColor Cyan
Write-Host "Fetching M1 bars from 2026-02-26 09:00 to 10:00 (São Paulo time)"
Write-Host ""

$env:PYTHONPATH = "c:\Documents backup\QUANT\qDATA"
python -m poetry run python3 -m quantwinmt5feeder.manual --start "2026-02-26 09:00" --end "2026-02-26 10:00"

Write-Host ""
pause
