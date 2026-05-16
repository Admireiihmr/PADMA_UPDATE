# PowerShell script to refresh Vision API credentials
# This can be scheduled to run daily using Windows Task Scheduler

Write-Host "Refreshing Vision API credentials..." -ForegroundColor Green
Write-Host "Time: $(Get-Date)" -ForegroundColor Cyan

# Change to the application directory
Set-Location "D:\dfu html"

try {
    # Check if the API is running and refresh credentials
    $response = Invoke-RestMethod -Uri "http://localhost:8000/refresh-credentials" -Method Get -TimeoutSec 30
    
    if ($response.status -eq "success") {
        Write-Host "✅ Credentials refreshed successfully" -ForegroundColor Green
        Write-Host "Message: $($response.message)" -ForegroundColor White
        Write-Host "Vision Client Ready: $($response.vision_client_ready)" -ForegroundColor White
    } else {
        Write-Host "❌ Failed to refresh credentials" -ForegroundColor Red
        Write-Host "Message: $($response.message)" -ForegroundColor Red
    }
} catch {
    Write-Host "❌ Error connecting to API: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "Make sure the API is running on localhost:8000" -ForegroundColor Yellow
}

Write-Host "Refresh attempt completed." -ForegroundColor Cyan
Write-Host "Press any key to continue..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
