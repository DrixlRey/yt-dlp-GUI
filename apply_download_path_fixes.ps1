# Apply download path fixes to current installation
Write-Host "Applying download path debug fixes..." -ForegroundColor Green

$sourceBase = "C:\Users\jackie.cheng\OneDrive - CDCR-CCHCS\powershell-scripts\Applications\yt-dl-installer"
$destBase = "C:\Program Files\YouTube Downloader GUI"

# Copy updated files with path fixes
Write-Host "Copying updated main_window.py with path debugging..."
Copy-Item -Path "$sourceBase\gui\main_window.py" -Destination "$destBase\gui\main_window.py" -Force

Write-Host "Copying updated config with correct Windows path..."
Copy-Item -Path "$sourceBase\config\app_config.json" -Destination "$destBase\config\app_config.json" -Force

Write-Host "Fixes applied successfully!" -ForegroundColor Green
Write-Host "Changes applied:" -ForegroundColor Cyan
Write-Host "  • Config now uses: C:\Users\jackie.cheng\Downloads" -ForegroundColor White
Write-Host "  • Show Folder button now opens correct location" -ForegroundColor White
Write-Host "  • Extensive debug output to console" -ForegroundColor White
Write-Host "  • Proper Windows path handling" -ForegroundColor White
Write-Host "" -ForegroundColor White
Write-Host "To test:" -ForegroundColor Green
Write-Host "  1. Run the app from Program Files" -ForegroundColor White
Write-Host "  2. Try downloading a video" -ForegroundColor White
Write-Host "  3. Check console output for DEBUG messages" -ForegroundColor White
Write-Host "  4. Click 'Show Folder' button in completion dialog" -ForegroundColor White
Write-Host "  5. Files should be in: C:\Users\jackie.cheng\Downloads" -ForegroundColor White