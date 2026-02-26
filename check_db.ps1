Write-Host "Querying the top 10 most recent OHLC bars from the QuantWin Database..." -ForegroundColor Cyan
Write-Host ""

$env:PGPASSWORD = "8asdja98!"

# Note: running psql via wsl because the postgres server is inside wsl
wsl -e psql -U postgres -h localhost -d postgres -c "SELECT id, symbol, timeframe, time_sp, open, high, low, close, tick_volume FROM ohlc_bars ORDER BY time DESC LIMIT 10;"

Write-Host ""
pause
