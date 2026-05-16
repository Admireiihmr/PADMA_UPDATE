@echo off
echo Refreshing Vision API credentials...
echo Time: %date% %time%

REM Change to the application directory
cd /d "D:\dfu html"

REM Check if the API is running and refresh credentials
curl -s "http://localhost:8000/refresh-credentials" > refresh_result.txt

REM Check the result
findstr "success" refresh_result.txt >nul
if %errorlevel% equ 0 (
    echo ✅ Credentials refreshed successfully
) else (
    echo ❌ Failed to refresh credentials
    echo Check refresh_result.txt for details
)

REM Clean up
del refresh_result.txt

echo Refresh attempt completed.
pause
