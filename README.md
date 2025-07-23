# YouTube Downloader GUI - System Installation

This is the installer version of YouTube Downloader GUI that installs dependencies system-wide instead of using embedded/portable versions.

## What This Installer Does

The NSIS installer will download and install:

1. **Python** (latest version) - System-wide installation to `C:\Program Files\Python3XX`
2. **PyQt6** - Installed via pip to system Python
3. **FFmpeg** - Installed to `C:\Program Files\FFmpeg` and added to system PATH
4. **yt-dlp** - Installed via pip to system Python
5. **YouTube Downloader GUI** - Installed to `C:\Program Files\YouTube Downloader GUI`

## Building the Installer

### Prerequisites
1. **NSIS** - Download from https://nsis.sourceforge.io/Download
2. **PowerShell** - For getting latest versions (included with Windows)
3. **Internet connection** - For downloading dependencies during build

### Build Steps
1. Open Command Prompt in the `yt-dl-installer` folder
2. Run: `build_installer.bat`

This will:
- Get the latest versions of Python, FFmpeg, and yt-dlp
- Create `versions.nsh` with download URLs
- Build `YouTube-Downloader-GUI-Installer.exe`

### Manual Build
If you prefer to build manually:

```cmd
REM Get latest versions
powershell -ExecutionPolicy Bypass -File get_latest_versions.ps1

REM Build installer with NSIS
"C:\Program Files (x86)\NSIS\makensis.exe" installer.nsi
```

## Installation Process

When users run the installer, it will:

1. **Download Python** - Latest stable version from python.org
2. **Install Python** - System-wide with PATH configuration
3. **Install PyQt6** - Via pip from the installed Python
4. **Download FFmpeg** - Latest from BtbN/FFmpeg-Builds
5. **Install FFmpeg** - Extract to Program Files and add to PATH
6. **Install yt-dlp** - Via pip from the installed Python
7. **Install GUI** - Copy application files and create shortcuts

## Differences from Portable Version

| Portable Version | System Installation |
|------------------|-------------------|
| 705MB total size | ~10MB installer |
| Self-contained | Uses system Python |
| No installation needed | Proper Windows installation |
| Embedded Python runtime | System-wide Python |
| Local FFmpeg binaries | FFmpeg in system PATH |
| Portable configuration | Standard app data locations |

## Advantages of System Installation

- **Smaller distribution** - Only ~10MB installer vs 705MB portable
- **Always up-to-date** - Downloads latest versions during installation
- **Proper uninstall** - Standard Windows Add/Remove Programs
- **Shared dependencies** - Python, PyQt6 can be used by other apps
- **System integration** - FFmpeg available system-wide
- **Standard installation** - Familiar Windows installer experience

## File Structure After Installation

```
C:\Program Files\YouTube Downloader GUI\
├── YouTube-Downloader-GUI.py          # Main application
├── YouTube-Downloader-GUI.cmd         # Launcher script
├── gui\                               # GUI modules
├── config\                            # Configuration
├── downloads\                         # Default download location
├── cache\                             # Application cache
├── logs\                              # Log files
└── app.ico                            # Application icon

System-wide:
C:\Program Files\Python3XX\            # Python installation
C:\Program Files\FFmpeg\               # FFmpeg binaries (in PATH)
```

## Troubleshooting

### Build Issues
- **NSIS not found**: Install NSIS from the official website
- **PowerShell execution policy**: Run as administrator or use `-ExecutionPolicy Bypass`
- **Internet connection**: Required for downloading latest versions

### Runtime Issues
- **Missing dependencies**: The app will show specific error messages for missing components
- **FFmpeg not found**: Ensure FFmpeg is in system PATH (installer handles this automatically)
- **PyQt6 issues**: Verify system-wide Python installation and pip packages

## Development Notes

- Modified `main.py` to use `SystemDependencyManager` instead of `EmbeddedDependencyManager`
- Configuration now uses `system_binaries` instead of `embedded_binaries`
- FFmpeg and yt-dlp are located via system PATH
- PyQt6 is imported from system Python installation