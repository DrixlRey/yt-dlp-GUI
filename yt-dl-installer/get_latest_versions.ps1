# Get Latest Versions Script for YouTube Downloader GUI Installer
# This script fetches the latest versions of Python, FFmpeg, and yt-dlp

Write-Host "Fetching latest versions..." -ForegroundColor Green

$versions = @{}

try {
    # Get latest Python version from python.org downloads page
    Write-Host "Getting latest Python version..." -ForegroundColor Yellow
    $pythonPage = Invoke-WebRequest "https://www.python.org/downloads/" -TimeoutSec 30
    $versionMatch = $pythonPage.Content | Select-String 'Download Python (\d+\.\d+\.\d+)'
    if ($versionMatch) {
        $pythonVersion = $versionMatch.Matches[0].Groups[1].Value
        $versions.Python = $pythonVersion
        Write-Host "Latest Python: $pythonVersion" -ForegroundColor Cyan
    } else {
        throw "Could not parse Python version from downloads page"
    }
} catch {
    Write-Host "Failed to get Python version, using fallback: 3.13.1" -ForegroundColor Red
    $versions.Python = "3.13.1"
}

try {
    # Get latest FFmpeg version
    Write-Host "Getting latest FFmpeg version..." -ForegroundColor Yellow
    $ffmpegAPI = Invoke-RestMethod "https://api.github.com/repos/BtbN/FFmpeg-Builds/releases/latest" -TimeoutSec 30
    $ffmpegVersion = $ffmpegAPI.tag_name
    $versions.FFmpeg = $ffmpegVersion
    Write-Host "Latest FFmpeg: $ffmpegVersion" -ForegroundColor Cyan
} catch {
    Write-Host "Failed to get FFmpeg version, using fallback: latest" -ForegroundColor Red
    $versions.FFmpeg = "latest"
}

try {
    # Get latest yt-dlp version
    Write-Host "Getting latest yt-dlp version..." -ForegroundColor Yellow
    $ytdlpAPI = Invoke-RestMethod "https://api.github.com/repos/yt-dlp/yt-dlp/releases/latest" -TimeoutSec 30
    $ytdlpVersion = $ytdlpAPI.tag_name
    $versions.YtDlp = $ytdlpVersion
    Write-Host "Latest yt-dlp: $ytdlpVersion" -ForegroundColor Cyan
} catch {
    Write-Host "Failed to get yt-dlp version, using fallback: latest" -ForegroundColor Red
    $versions.YtDlp = "latest"
}

# Create NSIS include file with version definitions
Write-Host "Creating NSIS version definitions..." -ForegroundColor Green

$nsisContent = @"
; Version definitions - Auto-generated on $(Get-Date)
!define PYTHON_VERSION "$($versions.Python)"
!define FFMPEG_VERSION "$($versions.FFmpeg)"
!define YTDLP_VERSION "$($versions.YtDlp)"

; Download URLs
!define PYTHON_URL "https://www.python.org/ftp/python/$($versions.Python)/python-$($versions.Python)-amd64.exe"
!define FFMPEG_URL "https://github.com/BtbN/FFmpeg-Builds/releases/download/$($versions.FFmpeg)/ffmpeg-master-latest-win64-gpl.zip"
!define YTDLP_URL "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe"

; Installation paths
!define PYTHON_INSTALL_DIR "`$PROGRAMFILES64\Python$($versions.Python -replace '\.', '')"
!define FFMPEG_INSTALL_DIR "`$PROGRAMFILES64\FFmpeg"
!define APP_INSTALL_DIR "`$PROGRAMFILES64\YouTube Downloader GUI"
"@

try {
    $nsisContent | Out-File -FilePath "versions.nsh" -Encoding UTF8
    Write-Host "Successfully created versions.nsh" -ForegroundColor Green
} catch {
    Write-Host "Failed to create versions.nsh: $_" -ForegroundColor Red
    exit 1
}

# Display summary
Write-Host "`n=== VERSION SUMMARY ===" -ForegroundColor Magenta
Write-Host "Python: $($versions.Python)" -ForegroundColor White
Write-Host "FFmpeg: $($versions.FFmpeg)" -ForegroundColor White
Write-Host "yt-dlp: $($versions.YtDlp)" -ForegroundColor White
Write-Host "NSIS definitions saved to versions.nsh" -ForegroundColor Green