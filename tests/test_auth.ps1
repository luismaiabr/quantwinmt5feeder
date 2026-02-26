Write-Host "Testing QuantWin REST API Authentication..." -ForegroundColor Cyan
Write-Host "This will request a fresh token using credentials from .env"
Write-Host ""

Set-Location -Path $PSScriptRoot\..
$env:PYTHONPATH = "c:\Documents backup\QUANT\qDATA"
python -m poetry run python -c "from quantwinmt5feeder.auth import TokenManager; tm = TokenManager(); tm.fetch_token(); print('\n[SUCCESS] Token fetched! First 20 chars:', tm.get_token()[:20])"

Write-Host ""
pause
