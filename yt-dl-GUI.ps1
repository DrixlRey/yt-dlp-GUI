Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

# Win32 API definitions for embedding CMD window
Add-Type @"
using System;
using System.Runtime.InteropServices;
using System.Diagnostics;

public class Win32 {
    [DllImport("user32.dll")]
    public static extern IntPtr SetParent(IntPtr hWndChild, IntPtr hWndNewParent);
    
    [DllImport("user32.dll")]
    public static extern bool SetWindowPos(IntPtr hWnd, IntPtr hWndInsertAfter, int X, int Y, int cx, int cy, uint uFlags);
    
    [DllImport("user32.dll")]
    public static extern int SetWindowLong(IntPtr hWnd, int nIndex, int dwNewLong);
    
    [DllImport("user32.dll")]
    public static extern int GetWindowLong(IntPtr hWnd, int nIndex);
    
    public const int GWL_STYLE = -16;
    public const int WS_CAPTION = 0x00C00000;
    public const int WS_THICKFRAME = 0x00040000;
    public const int WS_MINIMIZE = 0x20000000;
    public const int WS_MAXIMIZE = 0x01000000;
    public const int WS_SYSMENU = 0x00080000;
    public const uint SWP_NOZORDER = 0x0004;
    public const uint SWP_NOACTIVATE = 0x0010;
}
"@

# Global variables to track processes and jobs
$script:cmdProcess = $null
$script:bitsJob = $null

# Function to cleanup BITS jobs on exit
function Cleanup-BitsJobs {
    try {
        # Clean up any remaining BITS jobs from this session
        $allJobs = Get-BitsTransfer -AllUsers -ErrorAction SilentlyContinue
        foreach ($job in $allJobs) {
            if ($job.DisplayName -match "python-.*-installer\.exe" -or $job.JobState -eq "Error") {
                try {
                    Remove-BitsTransfer -JobId $job.JobId -Confirm:$false -ErrorAction SilentlyContinue
                } catch { }
            }
        }
    } catch { }
}

# Create the main form
$form = New-Object System.Windows.Forms.Form
$form.Text = "YouTube Downloader GUI"
$form.Size = New-Object System.Drawing.Size(595, 450)
$form.StartPosition = "CenterScreen"
$form.FormBorderStyle = [System.Windows.Forms.FormBorderStyle]::FixedSingle
$form.MaximizeBox = $false

# Create MenuStrip
$menuStrip = New-Object System.Windows.Forms.MenuStrip

# File Menu
$fileMenu = New-Object System.Windows.Forms.ToolStripMenuItem
$fileMenu.Text = "&File"

$openDownloadsMenuItem = New-Object System.Windows.Forms.ToolStripMenuItem
$openDownloadsMenuItem.Text = "Open &Downloads Folder"
$openDownloadsMenuItem.Add_Click({
    try {
        $downloadsPath = [Environment]::GetFolderPath([Environment+SpecialFolder]::UserProfile) + "\Downloads"
        if (Test-Path $downloadsPath) {
            Start-Process explorer.exe -ArgumentList $downloadsPath
        } else {
            [System.Windows.Forms.MessageBox]::Show("Downloads folder not found.", "Folder Not Found")
        }
    } catch {
        [System.Windows.Forms.MessageBox]::Show("Error opening downloads folder: $($_.Exception.Message)", "Error")
    }
})
$fileMenu.DropDownItems.Add($openDownloadsMenuItem) | Out-Null

$fileMenu.DropDownItems.Add("-") | Out-Null

$exitMenuItem = New-Object System.Windows.Forms.ToolStripMenuItem
$exitMenuItem.Text = "E&xit"
$exitMenuItem.Add_Click({
    $form.Close()
})
$fileMenu.DropDownItems.Add($exitMenuItem) | Out-Null

# Dependencies Menu
$dependenciesMenu = New-Object System.Windows.Forms.ToolStripMenuItem
$dependenciesMenu.Text = "&Dependencies"

$installPythonMenuItem = New-Object System.Windows.Forms.ToolStripMenuItem
$installPythonMenuItem.Text = "&Install Python"
$dependenciesMenu.DropDownItems.Add($installPythonMenuItem) | Out-Null

$checkPythonMenuItem = New-Object System.Windows.Forms.ToolStripMenuItem
$checkPythonMenuItem.Text = "&Check Python Status"
$dependenciesMenu.DropDownItems.Add($checkPythonMenuItem) | Out-Null

$dependenciesMenu.DropDownItems.Add("-") | Out-Null

$installYtDlpMenuItem = New-Object System.Windows.Forms.ToolStripMenuItem
$installYtDlpMenuItem.Text = "Install &yt-dlp"
$dependenciesMenu.DropDownItems.Add($installYtDlpMenuItem) | Out-Null

$checkYtDlpMenuItem = New-Object System.Windows.Forms.ToolStripMenuItem
$checkYtDlpMenuItem.Text = "Check yt-dlp &Status"
$dependenciesMenu.DropDownItems.Add($checkYtDlpMenuItem) | Out-Null

$dependenciesMenu.DropDownItems.Add("-") | Out-Null

$restartBitsMenuItem = New-Object System.Windows.Forms.ToolStripMenuItem
$restartBitsMenuItem.Text = "Restart &BITS Service"
$dependenciesMenu.DropDownItems.Add($restartBitsMenuItem) | Out-Null

# Help Menu
$helpMenu = New-Object System.Windows.Forms.ToolStripMenuItem
$helpMenu.Text = "&Help"

$installationGuideMenuItem = New-Object System.Windows.Forms.ToolStripMenuItem
$installationGuideMenuItem.Text = "&Dependencies Installation Guide"
$installationGuideMenuItem.Add_Click({
    $helpMessage = @"
🔧 Dependencies Installation Guide

IMPORTANT: Install dependencies in this order:

1️⃣ INSTALL PYTHON FIRST
   • Go to Dependencies > Install Python
   • Downloads latest Python version automatically
   • Shows real progress bar (0-100%)
   • Installs with PATH configuration

2️⃣ INSTALL YT-DLP SECOND  
   • Go to Dependencies > Check Python Status (verify installed)
   • Go to Dependencies > Install yt-dlp
   • Installation shows in GUI console
"@
    
    [System.Windows.Forms.MessageBox]::Show($helpMessage, "Dependencies Installation Guide", [System.Windows.Forms.MessageBoxButtons]::OK, [System.Windows.Forms.MessageBoxIcon]::Information)
})
$helpMenu.DropDownItems.Add($installationGuideMenuItem) | Out-Null

$helpMenu.DropDownItems.Add("-") | Out-Null

$aboutMenuItem = New-Object System.Windows.Forms.ToolStripMenuItem
$aboutMenuItem.Text = "&About"
$aboutMenuItem.Add_Click({
    [System.Windows.Forms.MessageBox]::Show("YouTube Downloader GUI v1.0`n`nA PowerShell-based YouTube downloader with embedded Python installer.", "About", [System.Windows.Forms.MessageBoxButtons]::OK, [System.Windows.Forms.MessageBoxIcon]::Information)
})
$helpMenu.DropDownItems.Add($aboutMenuItem) | Out-Null

# Add menus to menu strip
$menuStrip.Items.Add($fileMenu) | Out-Null
$menuStrip.Items.Add($dependenciesMenu) | Out-Null
$menuStrip.Items.Add($helpMenu) | Out-Null

$form.MainMenuStrip = $menuStrip
$form.Controls.Add($menuStrip)

# Create StatusStrip at bottom of form
$global:StatusStrip = New-Object System.Windows.Forms.StatusStrip
$global:StatusLabel = New-Object System.Windows.Forms.ToolStripStatusLabel
$global:StatusLabel.Text = "YouTube Downloader ready"
$global:StatusLabel.Spring = $true
$global:StatusLabel.TextAlign = [System.Drawing.ContentAlignment]::MiddleLeft
$global:StatusStrip.Items.Add($global:StatusLabel) | Out-Null

# Custom round status indicator for Python
$global:PythonStatusLabel = New-Object System.Windows.Forms.ToolStripStatusLabel
$global:PythonStatusLabel.Text = "● Python"
$global:PythonStatusLabel.ForeColor = [System.Drawing.Color]::Red
$global:PythonStatusLabel.ToolTipText = "Python installation status"
$global:StatusStrip.Items.Add($global:PythonStatusLabel) | Out-Null

# Custom round status indicator for yt-dlp
$global:YtDlpStatusLabel = New-Object System.Windows.Forms.ToolStripStatusLabel
$global:YtDlpStatusLabel.Text = "● yt-dlp"
$global:YtDlpStatusLabel.ForeColor = [System.Drawing.Color]::Red
$global:YtDlpStatusLabel.ToolTipText = "yt-dlp installation status"
$global:StatusStrip.Items.Add($global:YtDlpStatusLabel) | Out-Null

$form.Controls.Add($global:StatusStrip)

# Function to update Python status indicator
function Update-PythonStatusIndicator {
    param(
        [bool]$Installed,
        [string]$Version = "",
        [string]$Method = ""
    )
    
    if ($Installed) {
        $global:PythonStatusLabel.ForeColor = [System.Drawing.Color]::Green
        $tooltipText = "Python is installed"
        if ($Version) { $tooltipText += ": $Version" }
        if ($Method) { $tooltipText += " (via $Method)" }
        $global:PythonStatusLabel.ToolTipText = $tooltipText
    } else {
        $global:PythonStatusLabel.ForeColor = [System.Drawing.Color]::Red
        $global:PythonStatusLabel.ToolTipText = "Python is not installed or not in PATH"
    }
}

# Function to update yt-dlp status indicator
function Update-YtDlpStatusIndicator {
    param(
        [bool]$Installed,
        [string]$Version = "",
        [string]$Method = ""
    )
    
    if ($Installed) {
        $global:YtDlpStatusLabel.ForeColor = [System.Drawing.Color]::Green
        $tooltipText = "yt-dlp is installed"
        if ($Version) { $tooltipText += ": $Version" }
        if ($Method) { $tooltipText += " (via $Method)" }
        $global:YtDlpStatusLabel.ToolTipText = $tooltipText
    } else {
        $global:YtDlpStatusLabel.ForeColor = [System.Drawing.Color]::Red
        $global:YtDlpStatusLabel.ToolTipText = "yt-dlp is not installed"
    }
}

# URL Input Label
$urlLabel = New-Object System.Windows.Forms.Label
$urlLabel.Location = New-Object System.Drawing.Point(10, 35)
$urlLabel.Size = New-Object System.Drawing.Size(200, 20)
$urlLabel.Text = "YouTube URL:"
$form.Controls.Add($urlLabel)

# URL Input TextBox
$urlTextBox = New-Object System.Windows.Forms.TextBox
$urlTextBox.Location = New-Object System.Drawing.Point(10, 60)
$urlTextBox.Size = New-Object System.Drawing.Size(560, 20)
$urlTextBox.Text = "Paste YouTube URL here..."
$urlTextBox.ForeColor = [System.Drawing.Color]::Gray
$form.Controls.Add($urlTextBox)

# Placeholder text behavior
$urlTextBox.Add_GotFocus({
    if ($urlTextBox.Text -eq "Paste YouTube URL here...") {
        $urlTextBox.Text = ""
        $urlTextBox.ForeColor = [System.Drawing.Color]::Black
    }
})

$urlTextBox.Add_LostFocus({
    if ($urlTextBox.Text -eq "") {
        $urlTextBox.Text = "Paste YouTube URL here..."
        $urlTextBox.ForeColor = [System.Drawing.Color]::Gray
    }
})

# Download Type Label
$typeLabel = New-Object System.Windows.Forms.Label
$typeLabel.Location = New-Object System.Drawing.Point(10, 95)
$typeLabel.Size = New-Object System.Drawing.Size(200, 20)
$typeLabel.Text = "Download Type:"
$form.Controls.Add($typeLabel)

# Audio Button
$audioButton = New-Object System.Windows.Forms.Button
$audioButton.Location = New-Object System.Drawing.Point(10, 120)
$audioButton.Size = New-Object System.Drawing.Size(120, 35)
$audioButton.Text = "Audio (MP3)"
$audioButton.BackColor = [System.Drawing.Color]::LightBlue
$form.Controls.Add($audioButton)

# Video Button
$videoButton = New-Object System.Windows.Forms.Button
$videoButton.Location = New-Object System.Drawing.Point(140, 120)
$videoButton.Size = New-Object System.Drawing.Size(120, 35)
$videoButton.Text = "Video (MP4)"
$videoButton.BackColor = [System.Drawing.Color]::LightGreen
$form.Controls.Add($videoButton)

# Video Quality GroupBox
$qualityGroupBox = New-Object System.Windows.Forms.GroupBox
$qualityGroupBox.Location = New-Object System.Drawing.Point(270, 90)
$qualityGroupBox.Size = New-Object System.Drawing.Size(120, 100)
$qualityGroupBox.Text = "Video Quality"
$form.Controls.Add($qualityGroupBox)

# Video Quality Radio Buttons (vertical layout inside GroupBox)
$bestQualityRadio = New-Object System.Windows.Forms.RadioButton
$bestQualityRadio.Location = New-Object System.Drawing.Point(10, 20)
$bestQualityRadio.Size = New-Object System.Drawing.Size(100, 18)
$bestQualityRadio.Text = "Best"
$bestQualityRadio.Checked = $true
$qualityGroupBox.Controls.Add($bestQualityRadio)

$quality1080Radio = New-Object System.Windows.Forms.RadioButton
$quality1080Radio.Location = New-Object System.Drawing.Point(10, 40)
$quality1080Radio.Size = New-Object System.Drawing.Size(100, 18)
$quality1080Radio.Text = "1080p Max"
$qualityGroupBox.Controls.Add($quality1080Radio)

$quality720Radio = New-Object System.Windows.Forms.RadioButton
$quality720Radio.Location = New-Object System.Drawing.Point(10, 60)
$quality720Radio.Size = New-Object System.Drawing.Size(100, 18)
$quality720Radio.Text = "720p Max"
$qualityGroupBox.Controls.Add($quality720Radio)

$quality480Radio = New-Object System.Windows.Forms.RadioButton
$quality480Radio.Location = New-Object System.Drawing.Point(10, 80)
$quality480Radio.Size = New-Object System.Drawing.Size(100, 18)
$quality480Radio.Text = "480p Max"
$qualityGroupBox.Controls.Add($quality480Radio)

# Console Panel to host embedded CMD window
$consolePanel = New-Object System.Windows.Forms.Panel
$consolePanel.Location = New-Object System.Drawing.Point(10, 200)
$consolePanel.Size = New-Object System.Drawing.Size(560, 180)
$consolePanel.BorderStyle = [System.Windows.Forms.BorderStyle]::Fixed3D
$consolePanel.BackColor = [System.Drawing.Color]::Black
$form.Controls.Add($consolePanel)

# Status label for console
$statusLabel = New-Object System.Windows.Forms.Label
$statusLabel.Location = New-Object System.Drawing.Point(20, 65)
$statusLabel.Size = New-Object System.Drawing.Size(520, 50)
$statusLabel.Text = "Ready to download. Paste a YouTube URL and click Audio or Video."
$statusLabel.ForeColor = [System.Drawing.Color]::Green
$statusLabel.Font = New-Object System.Drawing.Font("Consolas", 10)
$statusLabel.TextAlign = [System.Drawing.ContentAlignment]::MiddleCenter
$consolePanel.Controls.Add($statusLabel)

# Clear Output Button
$clearButton = New-Object System.Windows.Forms.Button
$clearButton.Location = New-Object System.Drawing.Point(453, 128)
$clearButton.Size = New-Object System.Drawing.Size(75, 25)
$clearButton.Text = "Clear"
$clearButton.Add_Click({
    $statusLabel.Text = "Console cleared."
    # Close any existing CMD process if running
    if ($script:cmdProcess -and !$script:cmdProcess.HasExited) {
        $script:cmdProcess.Kill()
    }
    $script:cmdProcess = $null
})
$form.Controls.Add($clearButton)


# Function to refresh environment PATH from registry
function Refresh-EnvironmentPath {
    try {
        # Get machine and user PATH from registry
        $machinePath = [Environment]::GetEnvironmentVariable("PATH", "Machine")
        $userPath = [Environment]::GetEnvironmentVariable("PATH", "User")
        
        # Combine them (user path takes precedence)
        $newPath = if ($userPath) { "$userPath;$machinePath" } else { $machinePath }
        
        # Update current session PATH
        $env:PATH = $newPath
        
        # Clear PowerShell's command cache to force re-discovery
        if (Get-Command Get-Command -ErrorAction SilentlyContinue) {
            # Clear the command cache
            [System.Management.Automation.CommandDiscovery]::ClearCache()
        }
        
        return $true
    }
    catch {
        return $false
    }
}

# Function to check yt-dlp installation status
function Test-YtDlpInstallation {
    try {
        # First ensure Python is available
        $pythonStatus = Test-PythonInstallation
        if (-not $pythonStatus.Installed) {
            return @{ 
                Installed = $false; 
                Version = $null; 
                Command = $null; 
                Method = "Python-not-found";
                Error = "Python is required but not installed"
            }
        }
        
        $pythonCmd = $pythonStatus.Command
        
        # Method 1: Check via pip show
        try {
            $pipShow = & $pythonCmd -m pip show yt-dlp 2>$null
            if ($pipShow) {
                $version = ($pipShow | Select-String "Version: (.+)").Matches[0].Groups[1].Value
                $location = ($pipShow | Select-String "Location: (.+)").Matches[0].Groups[1].Value
                return @{ 
                    Installed = $true; 
                    Version = $version; 
                    Command = "$pythonCmd -m yt_dlp"; 
                    Method = "pip-show";
                    Location = $location;
                    PythonCommand = $pythonCmd
                }
            }
        } catch { }
        
        # Method 2: Check via direct module import
        try {
            $moduleTest = & $pythonCmd -c "import yt_dlp; print(yt_dlp.__version__)" 2>$null
            if ($moduleTest -and $moduleTest -match "\d+\.\d+") {
                return @{ 
                    Installed = $true; 
                    Version = $moduleTest.Trim(); 
                    Command = "$pythonCmd -m yt_dlp"; 
                    Method = "module-import";
                    Location = "Python site-packages";
                    PythonCommand = $pythonCmd
                }
            }
        } catch { }
        
        # Method 3: Check if yt-dlp.exe is in PATH
        try {
            $ytdlpCmd = Get-Command yt-dlp -ErrorAction SilentlyContinue
            if ($ytdlpCmd) {
                $versionOutput = & yt-dlp --version 2>$null
                if ($versionOutput) {
                    return @{ 
                        Installed = $true; 
                        Version = $versionOutput.Trim(); 
                        Command = "yt-dlp"; 
                        Method = "PATH-executable";
                        Location = $ytdlpCmd.Source;
                        PythonCommand = $pythonCmd
                    }
                }
            }
        } catch { }
        
        # Method 4: Check Python Scripts directory
        try {
            $pythonPath = Split-Path $pythonCmd
            $scriptsPath = Join-Path $pythonPath "Scripts"
            $ytdlpExe = Join-Path $scriptsPath "yt-dlp.exe"
            
            if (Test-Path $ytdlpExe) {
                $versionOutput = & $ytdlpExe --version 2>$null
                if ($versionOutput) {
                    return @{ 
                        Installed = $true; 
                        Version = $versionOutput.Trim(); 
                        Command = $ytdlpExe; 
                        Method = "Scripts-directory";
                        Location = $ytdlpExe;
                        PythonCommand = $pythonCmd
                    }
                }
            }
        } catch { }
        
        return @{ 
            Installed = $false; 
            Version = $null; 
            Command = $null; 
            Method = "Not-found";
            Error = "yt-dlp not found in any expected location";
            PythonCommand = $pythonCmd
        }
        
    } catch {
        return @{ 
            Installed = $false; 
            Version = $null; 
            Command = $null; 
            Method = "Error";
            Error = $_.Exception.Message;
            PythonCommand = $null
        }
    }
}

# Function to check Python installation (enhanced with multiple detection methods)
function Test-PythonInstallation {
    try {
        # Method 1: Refresh PATH and try standard commands
        Refresh-EnvironmentPath | Out-Null
        
        # Try python command
        $pythonCmd = Get-Command python -ErrorAction SilentlyContinue
        if ($pythonCmd) {
            try {
                $version = & python --version 2>&1
                if ($version -and $version -match "Python") {
                    return @{ Installed = $true; Version = $version; Command = "python"; Method = "PATH-python" }
                }
            } catch { }
        }
        
        # Try python3 command
        $pythonCmd = Get-Command python3 -ErrorAction SilentlyContinue  
        if ($pythonCmd) {
            try {
                $version = & python3 --version 2>&1
                if ($version -and $version -match "Python") {
                    return @{ Installed = $true; Version = $version; Command = "python3"; Method = "PATH-python3" }
                }
            } catch { }
        }
        
        # Try py launcher
        $pythonCmd = Get-Command py -ErrorAction SilentlyContinue
        if ($pythonCmd) {
            try {
                $version = & py --version 2>&1
                if ($version -and $version -match "Python") {
                    return @{ Installed = $true; Version = $version; Command = "py"; Method = "PATH-py" }
                }
            } catch { }
        }
        
        # Method 2: Check common installation paths
        $commonPaths = @(
            "$env:LOCALAPPDATA\Programs\Python\Python*\python.exe",
            "$env:PROGRAMFILES\Python*\python.exe",
            "$env:PROGRAMFILES(x86)\Python*\python.exe",
            "$env:APPDATA\Local\Programs\Python\Python*\python.exe"
        )
        
        foreach ($pathPattern in $commonPaths) {
            $foundPaths = Get-ChildItem $pathPattern -ErrorAction SilentlyContinue | Sort-Object Name -Descending
            foreach ($pythonExe in $foundPaths) {
                try {
                    $version = & $pythonExe.FullName --version 2>&1
                    if ($version -and $version -match "Python") {
                        return @{ Installed = $true; Version = $version; Command = $pythonExe.FullName; Method = "Direct-path" }
                    }
                } catch { }
            }
        }
        
        # Method 3: Registry check
        try {
            $registryPaths = @(
                "HKLM:\SOFTWARE\Python\PythonCore",
                "HKCU:\SOFTWARE\Python\PythonCore"
            )
            
            foreach ($regPath in $registryPaths) {
                if (Test-Path $regPath) {
                    $pythonVersions = Get-ChildItem $regPath -ErrorAction SilentlyContinue | Sort-Object Name -Descending
                    foreach ($versionKey in $pythonVersions) {
                        try {
                            $installPath = Get-ItemProperty "$($versionKey.PSPath)\InstallPath" -Name "(default)" -ErrorAction SilentlyContinue
                            if ($installPath) {
                                $pythonExe = Join-Path $installPath."(default)" "python.exe"
                                if (Test-Path $pythonExe) {
                                    $version = & $pythonExe --version 2>&1
                                    if ($version -and $version -match "Python") {
                                        return @{ Installed = $true; Version = $version; Command = $pythonExe; Method = "Registry" }
                                    }
                                }
                            }
                        } catch { }
                    }
                }
            }
        } catch { }
        
        # Method 4: Fresh PowerShell process test
        try {
            $result = powershell.exe -Command "python --version" 2>$null
            if ($result -and $result -match "Python") {
                return @{ Installed = $true; Version = $result; Command = "python"; Method = "Fresh-process" }
            }
        } catch { }
        
        return @{ Installed = $false; Version = $null; Command = $null; Method = "Not-found" }
    }
    catch {
        return @{ Installed = $false; Version = $null; Command = $null; Method = "Error: $($_.Exception.Message)" }
    }
}

# Function to get latest Python version and download URL
function Get-LatestPythonInfo {
    try {
        # Try endoflife.date API first (most reliable for stable releases)
        $apiUrl = "https://endoflife.date/api/python.json"
        $response = Invoke-RestMethod -Uri $apiUrl -UseBasicParsing
        $latestRelease = $response[0]  # First element is latest stable
        $version = $latestRelease.latest
        
        # Construct download URL for Windows x64 installer
        $downloadUrl = "https://www.python.org/ftp/python/$version/python-$version-amd64.exe"
        
        return @{ Version = $version; DownloadUrl = $downloadUrl; Source = "endoflife.date" }
    }
    catch {
        try {
            # Fallback: Scrape python.org downloads page
            $downloadsUrl = "https://www.python.org/downloads/"
            $response = Invoke-WebRequest -Uri $downloadsUrl -UseBasicParsing
            $match = [regex]::Match($response.Content, 'Download Python (\d+\.\d+\.\d+)')
            
            if ($match.Success) {
                $version = $match.Groups[1].Value
                $downloadUrl = "https://www.python.org/ftp/python/$version/python-$version-amd64.exe"
                return @{ Version = $version; DownloadUrl = $downloadUrl; Source = "python.org scrape" }
            }
        }
        catch {
            # If scraping fails, continue to fallback
        }
        
        # Final fallback to known stable version
        $fallbackVersion = "3.13.5"
        $fallbackUrl = "https://www.python.org/ftp/python/$fallbackVersion/python-$fallbackVersion-amd64.exe"
        return @{ Version = $fallbackVersion; DownloadUrl = $fallbackUrl; Source = "fallback" }
    }
}

# Function to download and install Python (BITS transfer with real progress)
function Install-Python {
    try {
        # Get latest Python info
        $pythonInfo = Get-LatestPythonInfo
        
        # Create progress dialog
        $progressForm = New-Object System.Windows.Forms.Form
        $progressForm.Text = "Installing Python $($pythonInfo.Version)"
        $progressForm.Size = New-Object System.Drawing.Size(500, 200)
        $progressForm.StartPosition = "CenterParent"
        $progressForm.FormBorderStyle = [System.Windows.Forms.FormBorderStyle]::FixedDialog
        $progressForm.MaximizeBox = $false
        $progressForm.MinimizeBox = $false
        
        # Status label
        $progressLabel = New-Object System.Windows.Forms.Label
        $progressLabel.Location = New-Object System.Drawing.Point(20, 20)
        $progressLabel.Size = New-Object System.Drawing.Size(450, 20)
        $progressLabel.Text = "Preparing download from $($pythonInfo.Source)..."
        $progressForm.Controls.Add($progressLabel)
        
        # Progress bar (percentage-based)
        $progressBar = New-Object System.Windows.Forms.ProgressBar
        $progressBar.Location = New-Object System.Drawing.Point(20, 50)
        $progressBar.Size = New-Object System.Drawing.Size(450, 25)
        $progressBar.Style = [System.Windows.Forms.ProgressBarStyle]::Continuous
        $progressBar.Minimum = 0
        $progressBar.Maximum = 100
        $progressBar.Value = 0
        $progressForm.Controls.Add($progressBar)
        
        # Progress percentage label
        $percentLabel = New-Object System.Windows.Forms.Label
        $percentLabel.Location = New-Object System.Drawing.Point(430, 25)
        $percentLabel.Size = New-Object System.Drawing.Size(40, 20)
        $percentLabel.Text = "0%"
        $percentLabel.TextAlign = [System.Drawing.ContentAlignment]::MiddleRight
        $progressForm.Controls.Add($percentLabel)
        
        # Download details label
        $detailsLabel = New-Object System.Windows.Forms.Label
        $detailsLabel.Location = New-Object System.Drawing.Point(20, 85)
        $detailsLabel.Size = New-Object System.Drawing.Size(450, 20)
        $detailsLabel.Text = "Starting BITS transfer..."
        $progressForm.Controls.Add($detailsLabel)
        
        # Speed and ETA label
        $speedLabel = New-Object System.Windows.Forms.Label
        $speedLabel.Location = New-Object System.Drawing.Point(20, 105)
        $speedLabel.Size = New-Object System.Drawing.Size(450, 20)
        $speedLabel.Text = "Initializing download..."
        $progressForm.Controls.Add($speedLabel)
        
        # Cancel button
        $cancelButton = New-Object System.Windows.Forms.Button
        $cancelButton.Location = New-Object System.Drawing.Point(395, 135)
        $cancelButton.Size = New-Object System.Drawing.Size(75, 25)
        $cancelButton.Text = "Cancel"
        $script:downloadCancelled = $false
        $cancelButton.Add_Click({
            $script:downloadCancelled = $true
            try {
                if ($script:bitsJob) {
                    Remove-BitsTransfer $script:bitsJob.JobId -Confirm:$false -ErrorAction SilentlyContinue
                    $script:bitsJob = $null
                }
                # Additional cleanup of any orphaned jobs
                Cleanup-BitsJobs
            } catch { }
            $progressForm.Close()
        })
        $progressForm.Controls.Add($cancelButton)
        
        # Show progress form
        $progressForm.Show()
        $progressForm.Refresh()
        [System.Windows.Forms.Application]::DoEvents()
        
        # Setup temp file path
        $tempDir = [System.IO.Path]::GetTempPath()
        $installerPath = Join-Path $tempDir "python-$($pythonInfo.Version)-installer.exe"
        
        # Remove any existing file
        if (Test-Path $installerPath) {
            Remove-Item $installerPath -Force
        }
        
        try {
            # Add debugging info
            $progressLabel.Text = "Checking BITS service and starting download..."
            $detailsLabel.Text = "Source: $($pythonInfo.DownloadUrl)"
            $speedLabel.Text = "Destination: $installerPath"
            $progressForm.Refresh()
            [System.Windows.Forms.Application]::DoEvents()
            
            # Check BITS service
            try {
                $bitsService = Get-Service BITS -ErrorAction Stop
                if ($bitsService.Status -ne "Running") {
                    $progressForm.Close()
                    [System.Windows.Forms.MessageBox]::Show("BITS service is not running. Status: $($bitsService.Status)`n`nPlease start the BITS service or use Windows Update to enable it.", "BITS Service Error", [System.Windows.Forms.MessageBoxButtons]::OK, [System.Windows.Forms.MessageBoxIcon]::Error)
                    return
                }
            } catch {
                $progressForm.Close()
                [System.Windows.Forms.MessageBox]::Show("Cannot access BITS service: $($_.Exception.Message)`n`nBITS may not be available on this system.", "BITS Service Error", [System.Windows.Forms.MessageBoxButtons]::OK, [System.Windows.Forms.MessageBoxIcon]::Error)
                return
            }
            
            # Test URL accessibility
            try {
                $progressLabel.Text = "Testing download URL accessibility..."
                $progressForm.Refresh()
                [System.Windows.Forms.Application]::DoEvents()
                
                $webRequest = [System.Net.WebRequest]::Create($pythonInfo.DownloadUrl)
                $webRequest.Method = "HEAD"
                $webRequest.Timeout = 10000  # 10 seconds
                $response = $webRequest.GetResponse()
                $contentLength = $response.ContentLength
                $response.Close()
                
                $speedLabel.Text = "URL accessible, file size: $([Math]::Round($contentLength / 1MB, 2)) MB"
                $progressForm.Refresh()
                [System.Windows.Forms.Application]::DoEvents()
                Start-Sleep -Milliseconds 500
            } catch {
                $progressForm.Close()
                [System.Windows.Forms.MessageBox]::Show("Cannot access download URL: $($_.Exception.Message)`n`nURL: $($pythonInfo.DownloadUrl)`n`nPlease check your internet connection or try again later.", "Download URL Error", [System.Windows.Forms.MessageBoxButtons]::OK, [System.Windows.Forms.MessageBoxIcon]::Error)
                return
            }
            
            # Start BITS transfer with detailed error handling
            $progressLabel.Text = "Starting BITS download for Python $($pythonInfo.Version)..."
            $detailsLabel.Text = "Initializing BITS transfer..."
            $speedLabel.Text = "Please wait..."
            $progressForm.Refresh()
            [System.Windows.Forms.Application]::DoEvents()
            
            try {
                $script:bitsJob = Start-BitsTransfer -Source $pythonInfo.DownloadUrl -Destination $installerPath -Asynchronous -ErrorAction Stop
                $startTime = Get-Date
                $lastBytes = 0
                
                # Wait a moment for job to initialize
                Start-Sleep -Milliseconds 1000
                $script:bitsJob = Get-BitsTransfer -JobId $script:bitsJob.JobId
                
                $detailsLabel.Text = "BITS job created successfully, ID: $($script:bitsJob.JobId)"
                $speedLabel.Text = "Initial job state: $($script:bitsJob.JobState)"
                $progressForm.Refresh()
                [System.Windows.Forms.Application]::DoEvents()
                
            } catch {
                $progressForm.Close()
                [System.Windows.Forms.MessageBox]::Show("Failed to start BITS transfer: $($_.Exception.Message)`n`nThis could be due to:`n• Antivirus blocking the download`n• Group Policy restrictions`n• BITS configuration issues`n• Network connectivity problems", "BITS Transfer Error", [System.Windows.Forms.MessageBoxButtons]::OK, [System.Windows.Forms.MessageBoxIcon]::Error)
                return
            }
            
            # Monitor BITS transfer progress
            while ($script:bitsJob.JobState -eq "Transferring" -and !$script:downloadCancelled) {
                Start-Sleep -Milliseconds 500
                $script:bitsJob = Get-BitsTransfer -JobId $script:bitsJob.JobId
                
                # Calculate progress
                if ($script:bitsJob.BytesTotal -gt 0) {
                    $percent = [Math]::Round(($script:bitsJob.BytesTransferred / $script:bitsJob.BytesTotal) * 100, 1)
                    $transferredMB = [Math]::Round($script:bitsJob.BytesTransferred / 1MB, 2)
                    $totalMB = [Math]::Round($script:bitsJob.BytesTotal / 1MB, 2)
                    
                    # Calculate speed
                    $elapsed = (Get-Date) - $startTime
                    if ($elapsed.TotalSeconds -gt 0) {
                        $speedBps = $script:bitsJob.BytesTransferred / $elapsed.TotalSeconds
                        $speedMBps = [Math]::Round($speedBps / 1MB, 2)
                        
                        # Calculate ETA
                        $remainingBytes = $script:bitsJob.BytesTotal - $script:bitsJob.BytesTransferred
                        if ($speedBps -gt 0) {
                            $etaSeconds = [Math]::Round($remainingBytes / $speedBps)
                            $eta = if ($etaSeconds -lt 60) { "$etaSeconds sec" }
                                   elseif ($etaSeconds -lt 3600) { "$([Math]::Round($etaSeconds/60)) min" }
                                   else { "$([Math]::Round($etaSeconds/3600))h $([Math]::Round(($etaSeconds%3600)/60))m" }
                        } else { $eta = "calculating..." }
                    } else {
                        $speedMBps = 0
                        $eta = "calculating..."
                    }
                    
                    # Update UI
                    $progressBar.Value = [Math]::Min([Math]::Max($percent, 0), 100)
                    $percentLabel.Text = "$percent%"
                    $progressLabel.Text = "Downloading Python $($pythonInfo.Version) - $percent% complete"
                    $detailsLabel.Text = "$transferredMB MB / $totalMB MB downloaded"
                    $speedLabel.Text = "Speed: $speedMBps MB/s | ETA: $eta"
                    
                    $progressForm.Refresh()
                }
                
                [System.Windows.Forms.Application]::DoEvents()
            }
            
            if ($script:downloadCancelled) {
                if ($script:bitsJob) {
                    Remove-BitsTransfer $script:bitsJob.JobId -Confirm:$false
                }
                if (Test-Path $installerPath) { Remove-Item $installerPath -Force }
                $progressForm.Close()
                return
            }
            
            # Check final status
            if ($script:bitsJob.JobState -eq "Transferred") {
                # Complete the transfer
                Complete-BitsTransfer $script:bitsJob.JobId
                $script:bitsJob = $null  # Clear reference after completion
                
                $progressBar.Value = 100
                $percentLabel.Text = "100%"
                $progressLabel.Text = "Download complete! Launching installer..."
                $detailsLabel.Text = "Python installer ready"
                $speedLabel.Text = "Download completed successfully"
                $progressForm.Refresh()
                [System.Windows.Forms.Application]::DoEvents()
                
                Start-Sleep -Milliseconds 1000
                $progressForm.Close()
                
                # Verify file exists
                if (!(Test-Path $installerPath)) {
                    [System.Windows.Forms.MessageBox]::Show("Download completed but installer file not found. Please try again.", "File Error", [System.Windows.Forms.MessageBoxButtons]::OK, [System.Windows.Forms.MessageBoxIcon]::Error)
                    return
                }
                
                # Launch Python installer with pre-configured settings
                $installArgs = @(
                    "PrependPath=1",              # Add to PATH
                    "Include_doc=0",              # No documentation  
                    "Include_test=0",             # No test suite
                    "Include_dev=0",              # No dev tools
                    "Include_debug=0",            # No debug binaries
                    "Include_launcher=1",         # Include launcher
                    "InstallLauncherAllUsers=0"   # User-only launcher
                )
                
                # Start installer and monitor for close
                $process = Start-Process -FilePath $installerPath -ArgumentList $installArgs -PassThru
                
                # Monitor installer process in background (no popup)
                Start-Job -ScriptBlock {
                    param($processId, $jobId)
                    try {
                        $installerProcess = Get-Process -Id $processId -ErrorAction SilentlyContinue
                        if ($installerProcess) {
                            $installerProcess.WaitForExit()
                        }
                        # Installer closed, clean up any remaining BITS jobs
                        try {
                            $bitsJob = Get-BitsTransfer -JobId $jobId -ErrorAction SilentlyContinue
                            if ($bitsJob) {
                                Remove-BitsTransfer -JobId $jobId -Confirm:$false
                            }
                        } catch { }
                    } catch { }
                } -ArgumentList $process.Id, $script:bitsJob.JobId | Out-Null
                
                # Cleanup installer file after delay
                Start-Job -ScriptBlock {
                    param($path)
                    Start-Sleep -Seconds 180  # Give time for installation
                    if (Test-Path $path) { Remove-Item $path -Force }
                } -ArgumentList $installerPath | Out-Null
                
            } elseif ($script:bitsJob.JobState -eq "Error") {
                # Get detailed error information
                $errorDetails = @"
BITS Transfer Error Details:

Job State: $($script:bitsJob.JobState)
Error Description: $($script:bitsJob.ErrorDescription)
Error Context: $($script:bitsJob.ErrorContext)
Error Code: $($script:bitsJob.ErrorCode)

Source URL: $($pythonInfo.DownloadUrl)
Destination: $installerPath

This could be caused by:
• Network connectivity issues
• Antivirus/firewall blocking the download
• Server-side restrictions
• Insufficient disk space
• File permissions issues
"@
                Remove-BitsTransfer $script:bitsJob.JobId -Confirm:$false
                $progressForm.Close()
                [System.Windows.Forms.MessageBox]::Show($errorDetails, "BITS Download Error", [System.Windows.Forms.MessageBoxButtons]::OK, [System.Windows.Forms.MessageBoxIcon]::Error)
            } else {
                # Get detailed status information
                $statusDetails = @"
BITS Transfer Status Information:

Job State: $($script:bitsJob.JobState)
Bytes Transferred: $($script:bitsJob.BytesTransferred)
Bytes Total: $($script:bitsJob.BytesTotal)
Creation Time: $($script:bitsJob.CreationTime)
Modification Time: $($script:bitsJob.ModificationTime)

Source URL: $($pythonInfo.DownloadUrl)
Destination: $installerPath

Expected States: Transferring → Transferred
Actual State: $($script:bitsJob.JobState)

Possible reasons:
• Transfer suspended by system policy
• Network interruption
• Insufficient permissions
• System resource constraints
"@
                Remove-BitsTransfer $script:bitsJob.JobId -Confirm:$false
                $progressForm.Close()
                [System.Windows.Forms.MessageBox]::Show($statusDetails, "BITS Transfer Status", [System.Windows.Forms.MessageBoxButtons]::OK, [System.Windows.Forms.MessageBoxIcon]::Warning)
            }
            
        } catch {
            if ($script:bitsJob) {
                Remove-BitsTransfer $script:bitsJob.JobId -Confirm:$false
            }
            $progressForm.Close()
            [System.Windows.Forms.MessageBox]::Show("Error during BITS download: $($_.Exception.Message)", "Download Error", [System.Windows.Forms.MessageBoxButtons]::OK, [System.Windows.Forms.MessageBoxIcon]::Error)
        }
        
    } catch {
        if ($progressForm) { $progressForm.Close() }
        [System.Windows.Forms.MessageBox]::Show("Error setting up Python download: $($_.Exception.Message)", "Installation Error", [System.Windows.Forms.MessageBoxButtons]::OK, [System.Windows.Forms.MessageBoxIcon]::Error)
    }
}

# Function to validate URL
function Test-YouTubeURL {
    param([string]$url)
    
    if ([string]::IsNullOrWhiteSpace($url) -or $url -eq "Paste YouTube URL here...") {
        return $false
    }
    
    # Basic YouTube URL validation
    if ($url -match "youtube\.com|youtu\.be") {
        return $true
    }
    
    return $false
}

# Function to embed CMD window in the console panel
function Invoke-YTDownload {
    param(
        [string]$url,
        [string]$type
    )
    
    # Hide status label and prepare for embedded CMD
    $statusLabel.Visible = $false
    
    # Build the command
    if ($type -eq "Audio") {
        $arguments = "-f bestaudio --extract-audio --audio-format mp3 `"$url`""
    } else {
        # Determine video quality format based on selected radio button
        $videoFormat = ""
        if ($bestQualityRadio.Checked) {
            $videoFormat = "bv[ext=mp4][vcodec^=avc]+ba[ext=m4a]/best[ext=mp4]"
        } elseif ($quality1080Radio.Checked) {
            $videoFormat = "bv[ext=mp4][vcodec^=avc][height<=1080]+ba[ext=m4a]/bestvideo[ext=mp4][vcodec^=avc][height<=1080]+bestaudio[ext=m4a]/best[ext=mp4]"
        } elseif ($quality720Radio.Checked) {
            $videoFormat = "bv[ext=mp4][vcodec^=avc][height<=720]+ba[ext=m4a]/bestvideo[ext=mp4][vcodec^=avc][height<=720]+bestaudio[ext=m4a]/best[ext=mp4]"
        } elseif ($quality480Radio.Checked) {
            $videoFormat = "bv[ext=mp4][vcodec^=avc][height<=480]+ba[ext=m4a]/bestvideo[ext=mp4][vcodec^=avc][height<=480]+bestaudio[ext=m4a]/best[ext=mp4]"
        } else {
            # Default to best quality if nothing selected
            $videoFormat = "bv[ext=mp4][vcodec^=avc]+ba[ext=m4a]/best[ext=mp4]"
        }
        
        $arguments = "-f `"$videoFormat`" --merge-output-format mp4 `"$url`""
    }
    
    try {
        # Close any existing CMD process
        if ($script:cmdProcess -and !$script:cmdProcess.HasExited) {
            $script:cmdProcess.Kill()
        }
        
        # Start CMD process with yt-dlp command  
        $processStartInfo = New-Object System.Diagnostics.ProcessStartInfo
        $processStartInfo.FileName = "cmd.exe"
        $processStartInfo.Arguments = "/k yt-dlp $arguments && echo. && echo Download completed! Press any key to continue... && pause >nul"
        $processStartInfo.UseShellExecute = $true
        $processStartInfo.WindowStyle = [System.Diagnostics.ProcessWindowStyle]::Minimized
        
        # Start the process
        $script:cmdProcess = [System.Diagnostics.Process]::Start($processStartInfo)
        
        # Wait for the window to be created with retries
        $cmdHwnd = [IntPtr]::Zero
        $retries = 0
        while ($cmdHwnd -eq [IntPtr]::Zero -and $retries -lt 20) {
            Start-Sleep -Milliseconds 250
            $script:cmdProcess.Refresh()
            $cmdHwnd = $script:cmdProcess.MainWindowHandle
            $retries++
        }
        
        if ($cmdHwnd -ne [IntPtr]::Zero) {
            # Set the CMD window as child of our panel
            [Win32]::SetParent($cmdHwnd, $consolePanel.Handle)
            
            # Remove window decorations (title bar, borders)
            $style = [Win32]::GetWindowLong($cmdHwnd, [Win32]::GWL_STYLE)
            $newStyle = $style -band (-bnot ([Win32]::WS_CAPTION -bor [Win32]::WS_THICKFRAME -bor [Win32]::WS_MINIMIZE -bor [Win32]::WS_MAXIMIZE -bor [Win32]::WS_SYSMENU))
            [Win32]::SetWindowLong($cmdHwnd, [Win32]::GWL_STYLE, $newStyle)
            
            # Resize and position the CMD window to fit the panel
            [Win32]::SetWindowPos($cmdHwnd, [IntPtr]::Zero, 0, 0, $consolePanel.Width - 8, $consolePanel.Height - 8, [Win32]::SWP_NOZORDER -bor [Win32]::SWP_NOACTIVATE)
        } else {
            $statusLabel.Text = "❌ Could not get CMD window handle after $retries retries"
            $statusLabel.Visible = $true
            # Let CMD run normally if embedding fails
        }
        
    } catch {
        $statusLabel.Text = "❌ Error: $($_.Exception.Message)"
        $statusLabel.Visible = $true
    }
}

# Audio Button Click Event
$audioButton.Add_Click({
    $url = $urlTextBox.Text.Trim()
    
    if (-not (Test-YouTubeURL $url)) {
        [System.Windows.Forms.MessageBox]::Show("Please enter a valid YouTube URL.", "Invalid URL", [System.Windows.Forms.MessageBoxButtons]::OK, [System.Windows.Forms.MessageBoxIcon]::Warning)
        return
    }
    
    # Disable buttons during download
    $audioButton.Enabled = $false
    $videoButton.Enabled = $false
    
    try {
        Invoke-YTDownload -url $url -type "Audio"
    } finally {
        # Re-enable buttons
        $audioButton.Enabled = $true
        $videoButton.Enabled = $true
    }
})

# Video Button Click Event
$videoButton.Add_Click({
    $url = $urlTextBox.Text.Trim()
    
    if (-not (Test-YouTubeURL $url)) {
        [System.Windows.Forms.MessageBox]::Show("Please enter a valid YouTube URL.", "Invalid URL", [System.Windows.Forms.MessageBoxButtons]::OK, [System.Windows.Forms.MessageBoxIcon]::Warning)
        return
    }
    
    # Disable buttons during download
    $audioButton.Enabled = $false
    $videoButton.Enabled = $false
    
    try {
        Invoke-YTDownload -url $url -type "Video"
    } finally {
        # Re-enable buttons
        $audioButton.Enabled = $true
        $videoButton.Enabled = $true
    }
})

# Allow Enter key to trigger download (defaults to Audio)
$urlTextBox.Add_KeyDown({
    param($sender, $e)
    if ($e.KeyCode -eq [System.Windows.Forms.Keys]::Enter) {
        $audioButton.PerformClick()
    }
})

# Menu Event Handlers

# Install Python Menu Item Click
$installPythonMenuItem.Add_Click({
    Install-Python
})

# Check Python Status Menu Item Click  
$checkPythonMenuItem.Add_Click({
    # Show checking status
    $global:StatusLabel.Text = "Refreshing PATH and checking Python installation..."
    $form.Refresh()
    [System.Windows.Forms.Application]::DoEvents()
    
    $pythonStatus = Test-PythonInstallation
    if ($pythonStatus.Installed) {
        # Get additional info
        try {
            $pipVersion = & $pythonStatus.Command -m pip --version 2>$null
            $ytdlpInstalled = & $pythonStatus.Command -m pip show yt-dlp 2>$null
            $ytdlpStatus = if ($ytdlpInstalled) { 
                $ytdlpVersion = ($ytdlpInstalled | Select-String "Version: (.+)").Matches[0].Groups[1].Value
                "✅ Installed (v$ytdlpVersion)" 
            } else { 
                "❌ Not installed" 
            }
            
            $message = @"
✅ Python is installed and working correctly!

Version: $($pythonStatus.Version)
Command: $($pythonStatus.Command)
Detection Method: $($pythonStatus.Method)
Pip: $($pipVersion)
yt-dlp: $ytdlpStatus

Python is properly configured and ready to use.
"@
        } catch {
            $message = @"
✅ Python is installed and detected

Version: $($pythonStatus.Version)
Command: $($pythonStatus.Command)
Detection Method: $($pythonStatus.Method)

Note: Could not verify pip/yt-dlp status
Try running: $($pythonStatus.Command) -m pip --version
"@
        }
        
        [System.Windows.Forms.MessageBox]::Show($message, "Python Status - Detected", [System.Windows.Forms.MessageBoxButtons]::OK, [System.Windows.Forms.MessageBoxIcon]::Information)
        Update-PythonStatusIndicator -Installed $true -Version $pythonStatus.Version -Method $pythonStatus.Method
    } else {
        $detectionInfo = if ($pythonStatus.Method -and $pythonStatus.Method -ne "Not-found") {
            "`n`nDetection info: $($pythonStatus.Method)"
        } else {
            ""
        }
        
        $message = @"
❌ Python is not installed or not detectable

Checked the following locations:
• System PATH (after refresh from registry)
• Common installation directories
• Windows Registry entries
• Fresh PowerShell process test$detectionInfo

To install Python:
1. Go to Dependencies > Install Python
2. Download will show real progress (0-100%)
3. Installer launches with optimized settings
4. Python will be added to PATH automatically
5. Return here to verify installation

The auto-installer includes:
• Latest Python version detection
• Minimal components (faster install)
• User installation (no admin needed)
• Automatic PATH configuration
"@
        [System.Windows.Forms.MessageBox]::Show($message, "Python Status - Not Found", [System.Windows.Forms.MessageBoxButtons]::OK, [System.Windows.Forms.MessageBoxIcon]::Warning)
        Update-PythonStatusIndicator -Installed $false
    }
    
    $global:StatusLabel.Text = "YouTube Downloader ready"
})

# Install yt-dlp Menu Item Click
$installYtDlpMenuItem.Add_Click({
    $pythonStatus = Test-PythonInstallation
    if ($pythonStatus.Installed) {
        # Check if already installed
        try {
            $existingVersion = & $pythonStatus.Command -m pip show yt-dlp 2>$null
            if ($existingVersion -and $existingVersion -match "Version: (.+)") {
                $currentVersion = $matches[1]
                $result = [System.Windows.Forms.MessageBox]::Show("yt-dlp is already installed (version $currentVersion).`n`nDo you want to upgrade to the latest version?", "yt-dlp Already Installed", [System.Windows.Forms.MessageBoxButtons]::YesNo, [System.Windows.Forms.MessageBoxIcon]::Question)
                if ($result -eq [System.Windows.Forms.DialogResult]::No) {
                    return
                }
                $installArgs = @("-m", "pip", "install", "--upgrade", "yt-dlp")
                $action = "upgrade"
            } else {
                $installArgs = @("-m", "pip", "install", "yt-dlp")
                $action = "install"
            }
        } catch {
            $installArgs = @("-m", "pip", "install", "yt-dlp")
            $action = "install"
        }
        
        try {
            # Show progress and clear console
            $global:StatusLabel.Text = "Installing yt-dlp via pip..."
            $statusLabel.Text = "Starting yt-dlp installation..."
            $statusLabel.Visible = $true
            $form.Refresh()
            
            # Close any existing CMD process
            if ($script:cmdProcess -and !$script:cmdProcess.HasExited) {
                $script:cmdProcess.Kill()
            }
            $script:cmdProcess = $null
            
            # Build pip install command (installArgs already includes -m pip)
            $pipCommand = "$($pythonStatus.Command) $($installArgs -join ' ')"
            
            # Start CMD process with pip install command
            $processStartInfo = New-Object System.Diagnostics.ProcessStartInfo
            $processStartInfo.FileName = "cmd.exe"
            $processStartInfo.Arguments = "/k $pipCommand && echo. && echo yt-dlp installation completed! && timeout /t 3 >nul"
            $processStartInfo.UseShellExecute = $true
            $processStartInfo.WindowStyle = [System.Diagnostics.ProcessWindowStyle]::Minimized
            
            # Start the process
            $script:cmdProcess = [System.Diagnostics.Process]::Start($processStartInfo)
            
            # Wait for the window to be created
            $cmdHwnd = [IntPtr]::Zero
            $retries = 0
            while ($cmdHwnd -eq [IntPtr]::Zero -and $retries -lt 20) {
                Start-Sleep -Milliseconds 250
                $script:cmdProcess.Refresh()
                $cmdHwnd = $script:cmdProcess.MainWindowHandle
                $retries++
            }
            
            if ($cmdHwnd -ne [IntPtr]::Zero) {
                # Embed CMD window in console panel
                [Win32]::SetParent($cmdHwnd, $consolePanel.Handle)
                
                # Remove window decorations
                $style = [Win32]::GetWindowLong($cmdHwnd, [Win32]::GWL_STYLE)
                $newStyle = $style -band (-bnot ([Win32]::WS_CAPTION -bor [Win32]::WS_THICKFRAME -bor [Win32]::WS_MINIMIZE -bor [Win32]::WS_MAXIMIZE -bor [Win32]::WS_SYSMENU))
                [Win32]::SetWindowLong($cmdHwnd, [Win32]::GWL_STYLE, $newStyle)
                
                # Resize and position the CMD window
                [Win32]::SetWindowPos($cmdHwnd, [IntPtr]::Zero, 0, 0, $consolePanel.Width - 8, $consolePanel.Height - 8, [Win32]::SWP_NOZORDER -bor [Win32]::SWP_NOACTIVATE)
                
                # Hide status label since CMD is now visible
                $statusLabel.Visible = $false
            } else {
                $statusLabel.Text = "yt-dlp installation started in external window"
            }
            
            # Start background job to check completion and update status
            Start-Job -ScriptBlock {
                param($processId, $command)
                try {
                    $process = Get-Process -Id $processId -ErrorAction SilentlyContinue
                    if ($process) {
                        $process.WaitForExit()
                        return @{ Success = ($process.ExitCode -eq 0); ExitCode = $process.ExitCode }
                    }
                    return @{ Success = $false; ExitCode = -1 }
                } catch {
                    return @{ Success = $false; ExitCode = -1 }
                }
            } -ArgumentList $script:cmdProcess.Id, $pipCommand | Out-Null
            
            # Restore status and update indicators
            Start-Sleep -Seconds 2
            Update-PythonStatusIndicator -Installed $true -Version $pythonStatus.Version -Method $pythonStatus.Method
            $global:StatusLabel.Text = "yt-dlp installation completed"
            
        } catch {
            $statusLabel.Text = "Error during yt-dlp installation: $($_.Exception.Message)"
            $statusLabel.Visible = $true
            Update-PythonStatusIndicator -Installed $true -Version $pythonStatus.Version -Method $pythonStatus.Method
            $global:StatusLabel.Text = "YouTube Downloader ready"
        }
    } else {
        [System.Windows.Forms.MessageBox]::Show("Python is not installed or not available in PATH.`n`nPlease install Python first using:`nDependencies > Install Python", "Python Required", [System.Windows.Forms.MessageBoxButtons]::OK, [System.Windows.Forms.MessageBoxIcon]::Warning)
    }
})

# Check yt-dlp Status Menu Item Click
$checkYtDlpMenuItem.Add_Click({
    # Show checking status
    $global:StatusLabel.Text = "Checking yt-dlp installation..."
    $form.Refresh()
    [System.Windows.Forms.Application]::DoEvents()
    
    $ytdlpStatus = Test-YtDlpInstallation
    if ($ytdlpStatus.Installed) {
        # Get additional info about yt-dlp
        try {
            # Test if yt-dlp can actually run
            $testCommand = if ($ytdlpStatus.Method -eq "PATH-executable") { 
                "yt-dlp" 
            } else { 
                "$($ytdlpStatus.PythonCommand) -m yt_dlp" 
            }
            
            # Test basic functionality
            $helpTest = & $testCommand --help 2>$null | Select-Object -First 3
            $working = if ($helpTest -and ($helpTest -join " ") -match "yt-dlp") { "✅ Working" } else { "⚠️ May have issues" }
            
            # Get supported sites count
            $extractorsTest = & $testCommand --list-extractors 2>$null | Measure-Object -Line
            $supportedSites = if ($extractorsTest) { "$($extractorsTest.Lines) extractors" } else { "Unknown" }
            
            $message = @"
✅ yt-dlp is installed and ready!

Version: $($ytdlpStatus.Version)
Command: $($ytdlpStatus.Command)
Detection Method: $($ytdlpStatus.Method)
Location: $($ytdlpStatus.Location)
Python Command: $($ytdlpStatus.PythonCommand)
Status: $working
Supported Sites: $supportedSites

yt-dlp is properly configured for YouTube downloads.
You can now use the main interface to download videos.
"@
        } catch {
            $message = @"
✅ yt-dlp is installed

Version: $($ytdlpStatus.Version)
Command: $($ytdlpStatus.Command)
Detection Method: $($ytdlpStatus.Method)
Location: $($ytdlpStatus.Location)
Python Command: $($ytdlpStatus.PythonCommand)

Note: Could not test functionality
This may be normal if yt-dlp is still initializing.
"@
        }
        
        [System.Windows.Forms.MessageBox]::Show($message, "yt-dlp Status - Installed", [System.Windows.Forms.MessageBoxButtons]::OK, [System.Windows.Forms.MessageBoxIcon]::Information)
        
        # Update status indicators
        $pythonStatus = Test-PythonInstallation
        Update-PythonStatusIndicator -Installed $pythonStatus.Installed -Version $pythonStatus.Version -Method $pythonStatus.Method
        Update-YtDlpStatusIndicator -Installed $true -Version $ytdlpStatus.Version -Method $ytdlpStatus.Method
        
    } else {
        $errorInfo = if ($ytdlpStatus.Error) { "`n`nError details: $($ytdlpStatus.Error)" } else { "" }
        $pythonInfo = if ($ytdlpStatus.PythonCommand) { "`nPython found: $($ytdlpStatus.PythonCommand)" } else { "`nPython status: Not available" }
        
        $message = @"
❌ yt-dlp is not installed or not detectable

Detection Method: $($ytdlpStatus.Method)$pythonInfo$errorInfo

Checked locations:
• pip show yt-dlp (via Python module system)
• Python module import test
• yt-dlp.exe in system PATH
• Python Scripts directory

To install yt-dlp:
1. Ensure Python is installed first
2. Go to Dependencies > Install yt-dlp
3. Installation will show in GUI console
4. Return here to verify installation

Requirements:
• Python must be installed and working
• Internet connection for package download
• Sufficient disk space for yt-dlp package
"@
        [System.Windows.Forms.MessageBox]::Show($message, "yt-dlp Status - Not Found", [System.Windows.Forms.MessageBoxButtons]::OK, [System.Windows.Forms.MessageBoxIcon]::Warning)
        
        # Update status indicators
        $pythonStatus = Test-PythonInstallation
        Update-PythonStatusIndicator -Installed $pythonStatus.Installed -Version $pythonStatus.Version -Method $pythonStatus.Method
        Update-YtDlpStatusIndicator -Installed $false
    }
    
    $global:StatusLabel.Text = "YouTube Downloader ready"
})

# Restart BITS Service Menu Item Click
$restartBitsMenuItem.Add_Click({
    try {
        # Clean up any existing BITS jobs first
        Cleanup-BitsJobs
        
        # Get BITS service status
        $bitsService = Get-Service BITS -ErrorAction Stop
        $originalStatus = $bitsService.Status
        
        if ($bitsService.Status -eq "Running") {
            # Stop BITS service
            Stop-Service BITS -Force -ErrorAction Stop
            Start-Sleep -Seconds 2
        }
        
        # Start BITS service
        Start-Service BITS -ErrorAction Stop
        Start-Sleep -Seconds 2
        
        # Verify it's running
        $bitsService = Get-Service BITS
        if ($bitsService.Status -eq "Running") {
            [System.Windows.Forms.MessageBox]::Show("BITS service restarted successfully!`n`nOriginal Status: $originalStatus`nCurrent Status: $($bitsService.Status)`n`nYou can now try downloading Python again.", "BITS Service Restart", [System.Windows.Forms.MessageBoxButtons]::OK, [System.Windows.Forms.MessageBoxIcon]::Information)
        } else {
            [System.Windows.Forms.MessageBox]::Show("BITS service restart failed.`n`nCurrent Status: $($bitsService.Status)`n`nYou may need administrator privileges to restart the BITS service.", "BITS Service Error", [System.Windows.Forms.MessageBoxButtons]::OK, [System.Windows.Forms.MessageBoxIcon]::Warning)
        }
        
    } catch {
        [System.Windows.Forms.MessageBox]::Show("Error restarting BITS service: $($_.Exception.Message)`n`nThis operation requires administrator privileges. Try running PowerShell as administrator and use:`n`nRestart-Service BITS", "BITS Service Error", [System.Windows.Forms.MessageBoxButtons]::OK, [System.Windows.Forms.MessageBoxIcon]::Error)
    }
})

# Initialize status indicators on startup
$global:StatusLabel.Text = "Checking dependencies..."
$form.Refresh()

# Check Python status
$pythonStatus = Test-PythonInstallation
Update-PythonStatusIndicator -Installed $pythonStatus.Installed -Version $pythonStatus.Version -Method $pythonStatus.Method

# Check yt-dlp status
$ytdlpStatus = Test-YtDlpInstallation
Update-YtDlpStatusIndicator -Installed $ytdlpStatus.Installed -Version $ytdlpStatus.Version -Method $ytdlpStatus.Method

$global:StatusLabel.Text = "YouTube Downloader ready"

# Register cleanup on form close
Register-ObjectEvent -InputObject $form -EventName FormClosed -Action {
    Cleanup-BitsJobs
} | Out-Null

# Show the form
$form.ShowDialog() | Out-Null