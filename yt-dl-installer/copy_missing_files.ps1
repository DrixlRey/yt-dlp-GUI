# Copy missing downloader and dependencies folders to current installation
Write-Host "Copying missing modules to current installation..." -ForegroundColor Green

$sourceBase = "C:\Users\jackie.cheng\OneDrive - CDCR-CCHCS\powershell-scripts\Applications\yt-dl-installer"
$destBase = "C:\Program Files\YouTube Downloader GUI"

# Copy downloader folder
Write-Host "Copying downloader folder..."
Copy-Item -Path "$sourceBase\downloader" -Destination "$destBase\downloader" -Recurse -Force

# Copy dependencies folder
Write-Host "Copying dependencies folder..."
Copy-Item -Path "$sourceBase\dependencies" -Destination "$destBase\dependencies" -Recurse -Force

Write-Host "Done! Missing modules copied successfully." -ForegroundColor Green
Write-Host "You can now test the application." -ForegroundColor Cyan