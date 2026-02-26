# Start QuantWin MT5 Gap Filler
Write-Host "Starting QuantWin MT5 Gap Filler..." -ForegroundColor Cyan

# Set PYTHONPATH so Python can find the module
$env:PYTHONPATH = "c:\Documents backup\QUANT\qDATA"

# Run the python module
python -m poetry run python -m quantwinmt5feeder.gap_filler

if ($LASTEXITCODE -ne 0) {
    Write-Host "Gap Filler exited with an error code: $LASTEXITCODE" -ForegroundColor Red
} else {
    Write-Host "Gap Filler finished successfully." -ForegroundColor Green
}
