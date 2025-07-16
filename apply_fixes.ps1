# Apply download path and popup fixes to current installation
Write-Host "Applying download path and popup fixes..." -ForegroundColor Green

$sourceBase = "C:\Users\jackie.cheng\OneDrive - CDCR-CCHCS\powershell-scripts\Applications\yt-dl-installer"
$destBase = "C:\Program Files\YouTube Downloader GUI"

# Copy updated main_window.py with fixes
Write-Host "Copying updated main_window.py..."
Copy-Item -Path "$sourceBase\gui\main_window.py" -Destination "$destBase\gui\main_window.py" -Force

# Copy updated dialogs.py with settings
Write-Host "Copying updated dialogs.py..."
Copy-Item -Path "$sourceBase\gui\dialogs.py" -Destination "$destBase\gui\dialogs.py" -Force

Write-Host "Fixes applied successfully!" -ForegroundColor Green
Write-Host "Changes applied:" -ForegroundColor Cyan
Write-Host "  • Download path now uses configured default (~/Downloads)" -ForegroundColor White
Write-Host "  • Popup sizing fixed (400-500px width, proper layout)" -ForegroundColor White
Write-Host "  • Settings dialog fully functional" -ForegroundColor White
Write-Host "" -ForegroundColor White
Write-Host "You can now test the application with these fixes." -ForegroundColor Green