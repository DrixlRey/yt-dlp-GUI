Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

# Create the main form
$form = New-Object System.Windows.Forms.Form
$form.Text = "YouTube Downloader GUI"
$form.Size = New-Object System.Drawing.Size(600, 470) # Increased height
$form.StartPosition = "CenterScreen"
$form.FormBorderStyle = [System.Windows.Forms.FormBorderStyle]::FixedSingle
$form.MaximizeBox = $false

# URL Input Label
$urlLabel = New-Object System.Windows.Forms.Label
$urlLabel.Location = New-Object System.Drawing.Point(10, 20)
$urlLabel.Size = New-Object System.Drawing.Size(200, 20)
$urlLabel.Text = "YouTube URL:"
$form.Controls.Add($urlLabel)

# URL Input TextBox
$urlTextBox = New-Object System.Windows.Forms.TextBox
$urlTextBox.Location = New-Object System.Drawing.Point(10, 45)
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
$typeLabel.Location = New-Object System.Drawing.Point(10, 80)
$typeLabel.Size = New-Object System.Drawing.Size(200, 20)
$typeLabel.Text = "Download Type:"
$form.Controls.Add($typeLabel)

# Audio Button
$audioButton = New-Object System.Windows.Forms.Button
$audioButton.Location = New-Object System.Drawing.Point(10, 105)
$audioButton.Size = New-Object System.Drawing.Size(120, 35)
$audioButton.Text = "Audio (MP3)"
$audioButton.BackColor = [System.Drawing.Color]::LightBlue
$form.Controls.Add($audioButton)

# Video Button
$videoButton = New-Object System.Windows.Forms.Button
$videoButton.Location = New-Object System.Drawing.Point(140, 105)
$videoButton.Size = New-Object System.Drawing.Size(120, 35)
$videoButton.Text = "Video (MP4)"
$videoButton.BackColor = [System.Drawing.Color]::LightGreen
$form.Controls.Add($videoButton)

# Output/Console TextBox
$outputTextBox = New-Object System.Windows.Forms.TextBox
$outputTextBox.Location = New-Object System.Drawing.Point(10, 200) # Moved lower
$outputTextBox.Size = New-Object System.Drawing.Size(560, 180) # Original height
$outputTextBox.Multiline = $true
$outputTextBox.ScrollBars = [System.Windows.Forms.ScrollBars]::Vertical
$outputTextBox.ReadOnly = $true
$outputTextBox.Font = New-Object System.Drawing.Font("Consolas", 9)
$outputTextBox.Text = "Ready to download. Paste a YouTube URL and click Audio or Video."
$form.Controls.Add($outputTextBox)

# Clear Output Button
$clearButton = New-Object System.Windows.Forms.Button
$clearButton.Location = New-Object System.Drawing.Point(495, 395) # Moved to bottom
$clearButton.Size = New-Object System.Drawing.Size(75, 25)
$clearButton.Text = "Clear"
$clearButton.Add_Click({
    $outputTextBox.Text = "Output cleared."
})
$form.Controls.Add($clearButton)

# Video Quality Selection Group
$qualityGroup = New-Object System.Windows.Forms.GroupBox
$qualityGroup.Location = New-Object System.Drawing.Point(280, 80)
$qualityGroup.Size = New-Object System.Drawing.Size(290, 110)
$qualityGroup.Text = "Video Quality"

# Max Quality Radio
$maxQualityRadio = New-Object System.Windows.Forms.RadioButton
$maxQualityRadio.Location = New-Object System.Drawing.Point(10, 20)
$maxQualityRadio.Size = New-Object System.Drawing.Size(270, 20)
$maxQualityRadio.Text = "Max Quality (best available)"
$maxQualityRadio.Checked = $true
$qualityGroup.Controls.Add($maxQualityRadio)

# 1080p Radio
$hd1080Radio = New-Object System.Windows.Forms.RadioButton
$hd1080Radio.Location = New-Object System.Drawing.Point(10, 40)
$hd1080Radio.Size = New-Object System.Drawing.Size(270, 20)
$hd1080Radio.Text = "1080p (best <= 1080p)"
$qualityGroup.Controls.Add($hd1080Radio)

# 720p Radio
$hd720Radio = New-Object System.Windows.Forms.RadioButton
$hd720Radio.Location = New-Object System.Drawing.Point(10, 60)
$hd720Radio.Size = New-Object System.Drawing.Size(270, 20)
$hd720Radio.Text = "720p (best <= 720p)"
$qualityGroup.Controls.Add($hd720Radio)

# 480p Radio
$sd480Radio = New-Object System.Windows.Forms.RadioButton
$sd480Radio.Location = New-Object System.Drawing.Point(10, 80)
$sd480Radio.Size = New-Object System.Drawing.Size(270, 20)
$sd480Radio.Text = "480p (best <= 480p)"
$qualityGroup.Controls.Add($sd480Radio)

$form.Controls.Add($qualityGroup)

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

# Function to run yt-dlp command with visible CMD window
function Invoke-YTDownload {
    param(
        [string]$url,
        [string]$type
    )
    
    # Clear output and show starting message
    $outputTextBox.Text = "Starting $type download...`r`n"
    $outputTextBox.Refresh()
    
    # Build the command
    if ($type -eq "Audio") {
        $arguments = "-f bestaudio --extract-audio --audio-format mp3 `"$url`""
    } else {
        $qualityArgs = ""
        if ($maxQualityRadio.Checked) {
            $qualityArgs = '"bv[ext=mp4][vcodec^=avc]+ba[ext=m4a]/best[ext=mp4]"'
        } elseif ($hd1080Radio.Checked) {
            $qualityArgs = '"bv[ext=mp4][vcodec^=avc][height<=1080]+ba[ext=m4a]/bestvideo[ext=mp4][vcodec^=avc][height<=1080]+bestaudio[ext=m4a]/best[ext=mp4]"'
        } elseif ($hd720Radio.Checked) {
            $qualityArgs = '"bv[ext=mp4][vcodec^=avc][height<=720]+ba[ext=m4a]/bestvideo[ext=mp4][vcodec^=avc][height<=720]+bestaudio[ext=m4a]/best[ext=mp4]"'
        } elseif ($sd480Radio.Checked) {
            $qualityArgs = '"bv[ext=mp4][vcodec^=avc][height<=480]+ba[ext=m4a]/bestvideo[ext=mp4][vcodec^=avc][height<=480]+bestaudio[ext=m4a]/best[ext=mp4]"'
        }
        $arguments = "-f $qualityArgs --merge-output-format mp4 `"$url`""
    }
    
    $outputTextBox.Text += "Command: yt-dlp $arguments`r`n"
    $outputTextBox.Text += "Opening command window to show progress...`r`n`r`n"
    $outputTextBox.Refresh()
    
    try {
        # Start the download process with VISIBLE CMD window
        $process = Start-Process -FilePath "cmd.exe" -ArgumentList "/c", "yt-dlp $arguments && echo Download completed! && pause" -NoNewWindow -Wait -PassThru
        
        # Wait for process to complete
        $process.WaitForExit()
        
        # Show completion status in GUI
        if ($process.ExitCode -eq 0) {
            $outputTextBox.Text += "✅ Download completed successfully!`r`n"
        } else {
            $outputTextBox.Text += "❌ Download may have failed. Check the command window for details.`r`n"
        }
        
    } catch {
        $outputTextBox.Text += "❌ Error: $($_.Exception.Message)`r`n"
    }
    
    $outputTextBox.Refresh()
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
    $audioButton.Enabled = $false
    $videoButton.Enabled = $false
    try {
        $qualityArgs = ""
        if ($maxQualityRadio.Checked) {
            $qualityArgs = '"bv[ext=mp4][vcodec^=avc]+ba[ext=m4a]/best[ext=mp4]"'
        } elseif ($hd1080Radio.Checked) {
            $qualityArgs = '"bv[ext=mp4][vcodec^=avc][height<=1080]+ba[ext=m4a]/bestvideo[ext=mp4][vcodec^=avc][height<=1080]+bestaudio[ext=m4a]/best[ext=mp4]"'
        } elseif ($hd720Radio.Checked) {
            $qualityArgs = '"bv[ext=mp4][vcodec^=avc][height<=720]+ba[ext=m4a]/bestvideo[ext=mp4][vcodec^=avc][height<=720]+bestaudio[ext=m4a]/best[ext=mp4]"'
        } elseif ($sd480Radio.Checked) {
            $qualityArgs = '"bv[ext=mp4][vcodec^=avc][height<=480]+ba[ext=m4a]/bestvideo[ext=mp4][vcodec^=avc][height<=480]+bestaudio[ext=m4a]/best[ext=mp4]"'
        }
        $arguments = "-f $qualityArgs --merge-output-format mp4 `"$url`""
        $outputTextBox.Text = "Starting Video download...`r`n"
        $outputTextBox.Text += "Command: yt-dlp $arguments`r`n"
        $outputTextBox.Text += "Opening command window to show progress...`r`n`r`n"
        $outputTextBox.Refresh()
        $process = Start-Process -FilePath "cmd.exe" -ArgumentList "/c", "yt-dlp $arguments && echo Download completed! && pause" -NoNewWindow -Wait -PassThru
        if ($process.ExitCode -eq 0) {
            $outputTextBox.Text += "✅ Download completed successfully!`r`n"
        } else {
            $outputTextBox.Text += "❌ Download may have failed. Check the command window for details.`r`n"
        }
    } catch {
        $outputTextBox.Text += "❌ Error: $($_.Exception.Message)`r`n"
    }
    $audioButton.Enabled = $true
    $videoButton.Enabled = $true
    $outputTextBox.Refresh()
})

# Allow Enter key to trigger download (defaults to Audio)
$urlTextBox.Add_KeyDown({
    param($sender, $e)
    if ($e.KeyCode -eq [System.Windows.Forms.Keys]::Enter) {
        $audioButton.PerformClick()
    }
})

# Show the form
$form.ShowDialog() | Out-Null