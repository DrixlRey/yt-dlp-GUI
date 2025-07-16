Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
Add-Type -AssemblyName System.DirectoryServices

# Initialize global variables for original script compatibility
$global:ADSuitePaths = @{
    Exports = Join-Path $env:USERPROFILE "Desktop\ADExports"
}

# Ensure export directory exists
if (-not (Test-Path $global:ADSuitePaths.Exports)) {
    New-Item -Path $global:ADSuitePaths.Exports -ItemType Directory -Force | Out-Null
}

# Define the main form - PROPER SIZE FOR INTEGRATED TABS
$global:MainForm = New-Object System.Windows.Forms.Form
$global:MainForm.Text = "AD Management Suite v1.0"
$global:MainForm.Size = New-Object System.Drawing.Size(520, 560)
$global:MainForm.StartPosition = "CenterScreen"
$global:MainForm.FormBorderStyle = [System.Windows.Forms.FormBorderStyle]::FixedSingle
$global:MainForm.MaximizeBox = $false
$global:MainForm.MinimizeBox = $true

# Create menu bar
$menuStrip = New-Object System.Windows.Forms.MenuStrip

# File Menu
$fileMenu = New-Object System.Windows.Forms.ToolStripMenuItem
$fileMenu.Text = "&File"

$exportMenuItem = New-Object System.Windows.Forms.ToolStripMenuItem
$exportMenuItem.Text = "Open &Exports Folder"
$exportMenuItem.Add_Click({
    try {
        if (Test-Path $global:ADSuitePaths.Exports) {
            Start-Process explorer.exe -ArgumentList $global:ADSuitePaths.Exports
        } else {
            [System.Windows.Forms.MessageBox]::Show("Exports folder not found: $($global:ADSuitePaths.Exports)", "Folder Not Found")
        }
    } catch {
        [System.Windows.Forms.MessageBox]::Show("Error opening exports folder: $($_.Exception.Message)", "Error")
    }
})
$fileMenu.DropDownItems.Add($exportMenuItem) | Out-Null

$fileMenu.DropDownItems.Add("-") | Out-Null

$exitMenuItem = New-Object System.Windows.Forms.ToolStripMenuItem
$exitMenuItem.Text = "E&xit"
$exitMenuItem.Add_Click({
    $global:MainForm.Close()
})
$fileMenu.DropDownItems.Add($exitMenuItem) | Out-Null

# Tools Menu
$toolsMenu = New-Object System.Windows.Forms.ToolStripMenuItem
$toolsMenu.Text = "&Tools"

$testConnectionMenuItem = New-Object System.Windows.Forms.ToolStripMenuItem
$testConnectionMenuItem.Text = "&Test AD Connection"
$testConnectionMenuItem.Add_Click({
    Test-ADConnectionDialog
})
$toolsMenu.DropDownItems.Add($testConnectionMenuItem) | Out-Null

# Help Menu
$helpMenu = New-Object System.Windows.Forms.ToolStripMenuItem
$helpMenu.Text = "&Help"

$aboutMenuItem = New-Object System.Windows.Forms.ToolStripMenuItem
$aboutMenuItem.Text = "&About"
$aboutMenuItem.Add_Click({
    [System.Windows.Forms.MessageBox]::Show("AD Management Suite v1.0`n`nA PowerShell-based Active Directory management tool.", "About", [System.Windows.Forms.MessageBoxButtons]::OK, [System.Windows.Forms.MessageBoxIcon]::Information)
})
$helpMenu.DropDownItems.Add($aboutMenuItem) | Out-Null

# Add menus to menu strip
$menuStrip.Items.Add($fileMenu) | Out-Null
$menuStrip.Items.Add($toolsMenu) | Out-Null
$menuStrip.Items.Add($helpMenu) | Out-Null

$global:MainForm.MainMenuStrip = $menuStrip
$global:MainForm.Controls.Add($menuStrip)

# Create status bar FIRST so TabControl can position around it
$global:StatusStrip = New-Object System.Windows.Forms.StatusStrip
$global:StatusLabel = New-Object System.Windows.Forms.ToolStripStatusLabel
$global:StatusLabel.Text = "AD Management Suite loaded successfully"
$global:StatusLabel.Spring = $true
$global:StatusLabel.TextAlign = [System.Drawing.ContentAlignment]::MiddleLeft
$global:StatusStrip.Items.Add($global:StatusLabel) | Out-Null

# Add connection status indicator
$global:ConnectionStatusLabel = New-Object System.Windows.Forms.ToolStripStatusLabel
$global:ConnectionStatusLabel.Text = "AD: Connection Failed"
$global:ConnectionStatusLabel.ForeColor = [System.Drawing.Color]::Red
$global:StatusStrip.Items.Add($global:ConnectionStatusLabel) | Out-Null

$global:MainForm.Controls.Add($global:StatusStrip)

# PROPERLY INTEGRATED TabControl - positioned to avoid menu and status bar
$global:TabControl = New-Object System.Windows.Forms.TabControl
$global:TabControl.Location = New-Object System.Drawing.Point(5, 30)
$global:TabControl.Size = New-Object System.Drawing.Size(505, 485)
$global:TabControl.Anchor = [System.Windows.Forms.AnchorStyles]::Top -bor [System.Windows.Forms.AnchorStyles]::Bottom -bor [System.Windows.Forms.AnchorStyles]::Left -bor [System.Windows.Forms.AnchorStyles]::Right

# Create Tab Pages with proper integration
$global:GroupMembershipTab = New-Object System.Windows.Forms.TabPage
$global:GroupMembershipTab.Text = "Group Membership"
$global:GroupMembershipTab.Name = "GroupMembershipTab"
$global:GroupMembershipTab.UseVisualStyleBackColor = $true

$global:MoveOUTab = New-Object System.Windows.Forms.TabPage
$global:MoveOUTab.Text = "Move OU"  
$global:MoveOUTab.Name = "MoveOUTab"
$global:MoveOUTab.UseVisualStyleBackColor = $true

# ADD BOTH TABS TO TABCONTROL
[void]$global:TabControl.TabPages.Add($global:GroupMembershipTab)
[void]$global:TabControl.TabPages.Add($global:MoveOUTab)

# Add TabControl to form - will integrate properly with menu and status bar
$global:MainForm.Controls.Add($global:TabControl)

# ========== GROUP MEMBERSHIP TAB CONTENT ==========

# Define the group names
$groupNames = @(
"AD-CDCR-Units-PCsRestrictedGroups-Filter",
"App-CDCR-O365Licensing-Project",
"App-CDCR-O365Licensing-Visio",
"App-CDCR-SCCM-ChromeDevelopers",
"App-CDCR-SCCM-M365-Access",
"Share-CDCR-EIS-SAN2-RDCALC-M"
)

# File Path Label - PROPER WIDTH WITH PADDING
$filePathLabel1 = New-Object System.Windows.Forms.Label
$filePathLabel1.Location = New-Object System.Drawing.Point(10, 20)
$filePathLabel1.Size = New-Object System.Drawing.Size(460, 20)
$filePathLabel1.Text = "No file selected"
$global:GroupMembershipTab.Controls.Add($filePathLabel1)

# Browse Button
$openFileButton1 = New-Object System.Windows.Forms.Button
$openFileButton1.Location = New-Object System.Drawing.Point(10, 50)
$openFileButton1.Size = New-Object System.Drawing.Size(75, 25)
$openFileButton1.Text = "Browse"
$global:GroupMembershipTab.Controls.Add($openFileButton1)

$openFileDialog1 = New-Object System.Windows.Forms.OpenFileDialog
$openFileDialog1.Filter = "CSV files (*.csv)|*.csv"
$openFileDialog1.Title = "Select a CSV File"

# Manual sAMAccountName Label
$manualTextBoxLabel1 = New-Object System.Windows.Forms.Label
$manualTextBoxLabel1.Location = New-Object System.Drawing.Point(10, 85)
$manualTextBoxLabel1.Size = New-Object System.Drawing.Size(150, 20)
$manualTextBoxLabel1.Text = "Enter sAMAccountName"
$global:GroupMembershipTab.Controls.Add($manualTextBoxLabel1)

# Manual sAMAccountName TextBox - PROPER WIDTH WITH PADDING
$manualTextBox1 = New-Object System.Windows.Forms.TextBox
$manualTextBox1.Location = New-Object System.Drawing.Point(10, 110)
$manualTextBox1.Size = New-Object System.Drawing.Size(460, 20)
$manualTextBox1.Text = ""
$global:GroupMembershipTab.Controls.Add($manualTextBox1)

# Group ComboBox Label
$groupComboBoxLabel1 = New-Object System.Windows.Forms.Label
$groupComboBoxLabel1.Location = New-Object System.Drawing.Point(10, 140)
$groupComboBoxLabel1.Size = New-Object System.Drawing.Size(200, 20)
$groupComboBoxLabel1.Text = "Choose group membership"
$global:GroupMembershipTab.Controls.Add($groupComboBoxLabel1)

# Group ComboBox - PROPER WIDTH WITH DROPDOWN
$groupComboBox1 = New-Object System.Windows.Forms.ComboBox
$groupComboBox1.Location = New-Object System.Drawing.Point(10, 165)
$groupComboBox1.Size = New-Object System.Drawing.Size(460, 20)
$groupComboBox1.DropDownStyle = [System.Windows.Forms.ComboBoxStyle]::DropDownList
$groupComboBox1.Items.AddRange($groupNames)
$global:GroupMembershipTab.Controls.Add($groupComboBox1)

# Container Type Label
$containerLabel1 = New-Object System.Windows.Forms.Label
$containerLabel1.Location = New-Object System.Drawing.Point(95, 200)
$containerLabel1.Size = New-Object System.Drawing.Size(160, 20)
$containerLabel1.Text = ""
$containerLabel1.ForeColor = [System.Drawing.Color]::Blue
$global:GroupMembershipTab.Controls.Add($containerLabel1)

# Process Button
$processButton1 = New-Object System.Windows.Forms.Button
$processButton1.Location = New-Object System.Drawing.Point(10, 195)
$processButton1.Size = New-Object System.Drawing.Size(75, 25)
$processButton1.Text = "Process"
$global:GroupMembershipTab.Controls.Add($processButton1)

# Output TextBox - PROPER WIDTH WITH PADDING
$outputTextBox1 = New-Object System.Windows.Forms.TextBox
$outputTextBox1.Location = New-Object System.Drawing.Point(10, 230)
$outputTextBox1.Size = New-Object System.Drawing.Size(460, 160)
$outputTextBox1.Multiline = $true
$outputTextBox1.ScrollBars = [System.Windows.Forms.ScrollBars]::Vertical
$outputTextBox1.ReadOnly = $true
$global:GroupMembershipTab.Controls.Add($outputTextBox1)

# Search TextBox - PROPER WIDTH WITH PADDING
$searchTextBox1 = New-Object System.Windows.Forms.TextBox
$searchTextBox1.Location = New-Object System.Drawing.Point(10, 400)
$searchTextBox1.Size = New-Object System.Drawing.Size(370, 20)
$global:GroupMembershipTab.Controls.Add($searchTextBox1)

# Search Button - PROPER POSITIONING
$searchButton1 = New-Object System.Windows.Forms.Button
$searchButton1.Location = New-Object System.Drawing.Point(390, 398)
$searchButton1.Size = New-Object System.Drawing.Size(80, 25)
$searchButton1.Text = "Search"
$global:GroupMembershipTab.Controls.Add($searchButton1)

# ========== MOVE OU TAB CONTENT ==========

# File Path Label - PROPER SIZING FOR MOVE OU TAB
$filePathLabel2 = New-Object System.Windows.Forms.Label
$filePathLabel2.Location = New-Object System.Drawing.Point(10, 20)
$filePathLabel2.Size = New-Object System.Drawing.Size(460, 20)
$filePathLabel2.Text = "No file selected"
$global:MoveOUTab.Controls.Add($filePathLabel2)

# Browse Button
$openFileButton2 = New-Object System.Windows.Forms.Button
$openFileButton2.Location = New-Object System.Drawing.Point(10, 50)
$openFileButton2.Size = New-Object System.Drawing.Size(75, 25)
$openFileButton2.Text = "Browse"
$global:MoveOUTab.Controls.Add($openFileButton2)

$openFileDialog2 = New-Object System.Windows.Forms.OpenFileDialog
$openFileDialog2.Filter = "CSV files (*.csv)|*.csv"
$openFileDialog2.Title = "Select a CSV File"

# Manual sAMAccountName Label
$manualLabel2 = New-Object System.Windows.Forms.Label
$manualLabel2.Location = New-Object System.Drawing.Point(10, 85)
$manualLabel2.Size = New-Object System.Drawing.Size(300, 20)
$manualLabel2.Text = "Single sAMAccountName (optional):"
$global:MoveOUTab.Controls.Add($manualLabel2)

# Manual sAMAccountName TextBox - PROPER SIZING FOR TAB
$manualTextBox2 = New-Object System.Windows.Forms.TextBox
$manualTextBox2.Location = New-Object System.Drawing.Point(10, 110)
$manualTextBox2.Size = New-Object System.Drawing.Size(460, 20)
$global:MoveOUTab.Controls.Add($manualTextBox2)

# Find Destination OU Button
$findOUButton2 = New-Object System.Windows.Forms.Button
$findOUButton2.Location = New-Object System.Drawing.Point(10, 150)
$findOUButton2.Size = New-Object System.Drawing.Size(150, 25)
$findOUButton2.Text = "Find Destination OU"
$global:MoveOUTab.Controls.Add($findOUButton2)

# Selected Destination OU Label - PROPER SIZING FOR TAB
$selectedOULabel2 = New-Object System.Windows.Forms.TextBox
$selectedOULabel2.Location = New-Object System.Drawing.Point(170, 155)
$selectedOULabel2.Size = New-Object System.Drawing.Size(300, 20)
$selectedOULabel2.ReadOnly = $true
$selectedOULabel2.BorderStyle = 'None'
$selectedOULabel2.ScrollBars = 'Horizontal'
$selectedOULabel2.Text = "No Destination OU selected"
$global:MoveOUTab.Controls.Add($selectedOULabel2)

# Process Button
$processButton2 = New-Object System.Windows.Forms.Button
$processButton2.Location = New-Object System.Drawing.Point(10, 190)
$processButton2.Size = New-Object System.Drawing.Size(75, 25)
$processButton2.Text = "Process"
$global:MoveOUTab.Controls.Add($processButton2)

# Output TextBox - PROPER SIZING FOR TAB WITH MORE HEIGHT
$outputTextBox2 = New-Object System.Windows.Forms.TextBox
$outputTextBox2.Location = New-Object System.Drawing.Point(10, 230)
$outputTextBox2.Size = New-Object System.Drawing.Size(460, 200)
$outputTextBox2.Multiline = $true
$outputTextBox2.ScrollBars = [System.Windows.Forms.ScrollBars]::Vertical
$outputTextBox2.ReadOnly = $true
$global:MoveOUTab.Controls.Add($outputTextBox2)

# ========== HELPER FUNCTIONS ==========

function Set-StatusText {
    param([string]$Text)
    if ($global:StatusLabel) {
        $global:StatusLabel.Text = $Text
        $global:MainForm.Refresh()
    }
}

function Set-ConnectionStatus {
    param(
        [string]$Text,
        [string]$Color = "Black"
    )
    if ($global:ConnectionStatusLabel) {
        $global:ConnectionStatusLabel.Text = "AD: $Text"
        $colorObj = switch ($Color) {
            "Green" { [System.Drawing.Color]::Green }
            "Red" { [System.Drawing.Color]::Red }
            "Orange" { [System.Drawing.Color]::Orange }
            default { [System.Drawing.Color]::Black }
        }
        $global:ConnectionStatusLabel.ForeColor = $colorObj
        $global:MainForm.Refresh()
    }
}

function Test-ADConnectionDialog {
    try {
        Set-ConnectionStatus "Testing..." "Orange"
        $domain = [System.DirectoryServices.ActiveDirectory.Domain]::GetCurrentDomain()
        $domainName = $domain.Name
        $testUser = Get-ADUser -Filter * -ResultSetSize 1 -ErrorAction Stop
        Set-ConnectionStatus "Connected: $domainName" "Green"
        [System.Windows.Forms.MessageBox]::Show("Successfully connected to Active Directory domain: $domainName", "AD Connection Test", [System.Windows.Forms.MessageBoxButtons]::OK, [System.Windows.Forms.MessageBoxIcon]::Information)
    } catch {
        $errorMessage = $_.Exception.Message
        Set-ConnectionStatus "Connection Failed" "Red"
        [System.Windows.Forms.MessageBox]::Show("Failed to connect to Active Directory:`n`n$errorMessage", "AD Connection Test", [System.Windows.Forms.MessageBoxButtons]::OK, [System.Windows.Forms.MessageBoxIcon]::Warning)
    }
}

# ========== GROUP MEMBERSHIP EVENT HANDLERS ==========

$openFileButton1.Add_Click({
    $result = $openFileDialog1.ShowDialog()
    if ($result -eq [System.Windows.Forms.DialogResult]::OK) {
        $filePathLabel1.Text = $openFileDialog1.FileName
    }
})

$groupComboBox1.Add_SelectedIndexChanged({
    $selectedGroup = $groupComboBox1.SelectedItem
    switch ($selectedGroup) {
        "App-CDCR-SCCM-ChromeDevelopers" {$containerLabel1.Text = "(Computer container)"}
        "AD-CDCR-Units-PCsRestrictedGroups-Filter" { $containerLabel1.Text = "(User container)" }
        "App-CDCR-O365Licensing-Project"           { $containerLabel1.Text = "(User container)" }
        "App-CDCR-O365Licensing-Visio"               { $containerLabel1.Text = "(User container)" }
        "App-CDCR-SCCM-M365-Access"                  { $containerLabel1.Text = "(Computer container)" }
        "Share-CDCR-EIS-SAN2-RDCALC-M"               { $containerLabel1.Text = "(User container)" }
        Default                                      { $containerLabel1.Text = "" }
    }
})

# Include the original Group Membership Process button logic (condensed for space)
$processButton1.Add_Click({
    # CLEAR THE GUI CONSOLE BEFORE PROCESSING
    $outputTextBox1.Text = ""
    $outputTextBox1.Refresh()
    
    $output = ""
    
    if ($filePathLabel1.Text -eq "No file selected" -and $manualTextBox1.Text -eq "" -and $groupComboBox1.SelectedItem -eq $null) {
        [System.Windows.Forms.MessageBox]::Show("Please select a CSV file with sAMAccountName list or manually enter one in the box, and a group membership.", "Error", [System.Windows.Forms.MessageBoxButtons]::OK, [System.Windows.Forms.MessageBoxIcon]::Error)
        return
    }

    if ($filePathLabel1.Text -eq "No file selected" -and $manualTextBox1.Text -eq "") {
        [System.Windows.Forms.MessageBox]::Show("Please select a CSV file with sAMAccountName list or manually enter one in the box.", "Error", [System.Windows.Forms.MessageBoxButtons]::OK, [System.Windows.Forms.MessageBoxIcon]::Error)
        return
    }

    if ($groupComboBox1.SelectedItem -eq $null) {
        [System.Windows.Forms.MessageBox]::Show("Please select a group membership.", "Error", [System.Windows.Forms.MessageBoxButtons]::OK, [System.Windows.Forms.MessageBoxIcon]::Error)
        return
    }

    # Process CSV file if selected
    if ($filePathLabel1.Text -ne "No file selected") {
        try {
            $csvData = Import-Csv -Path $filePathLabel1.Text
            $groupName = $groupComboBox1.SelectedItem

            foreach ($row in $csvData) {
                $accountName = $row.samaccountname
                try {
                    $objectDN = (Get-ADUser -Filter "SamAccountName -eq '$accountName'" -Properties DistinguishedName -ErrorAction SilentlyContinue).DistinguishedName
                    if (-not $objectDN) {
                        $objectDN = (Get-ADComputer -Filter "SamAccountName -eq '$accountName$'" -Properties DistinguishedName -ErrorAction SilentlyContinue).DistinguishedName
                    }
                    if ($objectDN) {
                        Add-ADGroupMember -Identity $groupName -Members $objectDN -ErrorAction SilentlyContinue
                        $output += "Successfully added $accountName to $groupName.`r`n"
                        
                        # Membership verification
                        $groupMembers = Get-ADGroupMember -Identity $groupName -ErrorAction SilentlyContinue
                        $isMember = $false
                        foreach ($memberObj in $groupMembers) {
                            if ($memberObj.SamAccountName -eq $accountName -or $memberObj.SamAccountName -eq "$accountName`$") {
                                $isMember = $true
                                break
                            }
                        }
                        if ($isMember) {
                            $output += "isMember Check: $accountName is now in $groupName`r`n"
                        } else {
                            $output += "isMember Check: $accountName is NOT in $groupName`r`n"
                        }
                    } else {
                        $output += "Account $accountName not found as user or computer.`r`n"
                    }
                } catch {
                    $output += "Error adding $accountName to $groupName. Error: $($_.Exception.Message)`r`n"
                }
            }
        } catch {
            $output = "Error reading CSV file: $($_.Exception.Message)`r`n"
        }
        
        # EXPORT GROUP MEMBERSHIP RESULTS - APPEND TO EXISTING FILES
        try {
            $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
            $exportBase = if ($filePathLabel1.Text -ne "No file selected") {
                Split-Path -Parent $filePathLabel1.Text
            } else {
                $global:ADSuitePaths.Exports
            }
            
            # Create results object for export
            $results = @()
            foreach ($row in $csvData) {
                $accountName = $row.samaccountname
                $results += [PSCustomObject]@{
                    Timestamp = $timestamp
                    SamAccountName = $accountName
                    GroupName = $groupName
                    Operation = "Add Group Membership"
                    Status = if ($output -match "Successfully added $accountName") { "Success" } else { "Failed" }
                }
            }
            
            $exportPath = Join-Path $exportBase 'group_membership_log.csv'
            if (Test-Path $exportPath) {
                $results | Export-Csv -Path $exportPath -NoTypeInformation -Append
            } else {
                $results | Export-Csv -Path $exportPath -NoTypeInformation
            }
            
            $output += "`r`nExported results to: $exportBase (APPENDED with timestamp)`r`n"
        } catch {
            $output += "`r`nError exporting results: $($_.Exception.Message)`r`n"
        }
        
        $outputTextBox1.Text = $output
        return
    }

    # Process manual input
    if ($manualTextBox1.Text -ne "") {
        $accountName = $manualTextBox1.Text.Trim()
        $groupName = $groupComboBox1.SelectedItem
        try {
            $objectDN = (Get-ADUser -Filter "SamAccountName -eq '$accountName'" -Properties DistinguishedName -ErrorAction SilentlyContinue).DistinguishedName
            if (-not $objectDN) {
                $objectDN = (Get-ADComputer -Filter "SamAccountName -eq '$accountName$'" -Properties DistinguishedName -ErrorAction SilentlyContinue).DistinguishedName
            }
            if ($objectDN) {
                Add-ADGroupMember -Identity $groupName -Members $objectDN -ErrorAction SilentlyContinue
                $output += "Successfully added $accountName to $groupName.`r`n"
                
                # Membership verification
                $groupMembers = Get-ADGroupMember -Identity $groupName -ErrorAction SilentlyContinue
                $isMember = $false
                foreach ($memberObj in $groupMembers) {
                    if ($memberObj.SamAccountName -eq $accountName -or $memberObj.SamAccountName -eq "$accountName`$") {
                        $isMember = $true
                        break
                    }
                }
                if ($isMember) {
                    $output += "isMember Check: $accountName is now in $groupName`r`n"
                } else {
                    $output += "isMember Check: $accountName is NOT in $groupName`r`n"
                }
            } else {
                $output += "Account $accountName not found as user or computer.`r`n"
            }
        } catch {
            $output += "Error adding $accountName to $groupName. Error: $($_.Exception.Message)`r`n"
        }
        
        # EXPORT MANUAL INPUT RESULTS - APPEND TO EXISTING FILES
        try {
            $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
            $exportBase = $global:ADSuitePaths.Exports
            
            # Create results object for export
            $results = @([PSCustomObject]@{
                Timestamp = $timestamp
                SamAccountName = $accountName
                GroupName = $groupName
                Operation = "Add Group Membership (Manual)"
                Status = if ($output -match "Successfully added $accountName") { "Success" } else { "Failed" }
            })
            
            $exportPath = Join-Path $exportBase 'group_membership_log.csv'
            if (Test-Path $exportPath) {
                $results | Export-Csv -Path $exportPath -NoTypeInformation -Append
            } else {
                $results | Export-Csv -Path $exportPath -NoTypeInformation
            }
            
            $output += "`r`nExported results to: $exportBase (APPENDED with timestamp)`r`n"
        } catch {
            $output += "`r`nError exporting results: $($_.Exception.Message)`r`n"
        }
        
        $outputTextBox1.Text = $output
    }
})

# Include the original Search function (condensed)
$searchButton1.Add_Click({
    $searchTerm = $searchTextBox1.Text.Trim()
    if ($searchTerm -ne "") {
        try {
            $nameParts = $searchTerm -split "[\s.]+" 
            if ($nameParts.Count -eq 1) {
                $filter = "GivenName -like '*$searchTerm*' -or Surname -like '*$searchTerm*' -or SamAccountName -like '*$searchTerm*'"
            } elseif ($nameParts.Count -ge 2) {
                $filter = @"
(GivenName -like '*$($nameParts[0])*' -and Surname -like '*$($nameParts[1])*') 
-or (GivenName -like '*$($nameParts[1])*' -and Surname -like '*$($nameParts[0])*') 
-or (SamAccountName -like '*$($nameParts[0]).$($nameParts[1])*')
"@
            }
            $users = Get-ADUser -Filter $filter -Properties * -ErrorAction SilentlyContinue
            $computer = Get-ADComputer -Filter "SamAccountName -eq '$searchTerm$'" -Properties * -ErrorAction SilentlyContinue
            
            $dataTable = New-Object System.Data.DataTable
            $dataTable.Columns.Add("Type")
            $dataTable.Columns.Add("SamAccountName")
            $dataTable.Columns.Add("OU")
            $dataTable.Columns.Add("DistinguishedName")
            $dataTable.Columns.Add("DisplayName")
            $dataTable.Columns.Add("EmailAddress")
            $dataTable.Columns.Add("Title")
            $dataTable.Columns.Add("Department")
            $dataTable.Columns.Add("OperatingSystem")
            $dataTable.Columns.Add("LastLogonDate")
            
            function Get-LastOU {
                param ([string]$distinguishedName)
                $ouParts = $distinguishedName -split ','
                $lastOU = $ouParts | Where-Object { $_ -like 'OU=*' } | Select-Object -Last 1
                return ($lastOU -replace '^OU=', '').Trim()
            }
            
            if ($users) {
                foreach ($user in $users) {
                    $row = $dataTable.NewRow()
                    $row["Type"] = "User"
                    $row["SamAccountName"] = $user.SamAccountName
                    $row["OU"] = Get-LastOU -distinguishedName $user.DistinguishedName
                    $row["DistinguishedName"] = $user.DistinguishedName
                    $row["DisplayName"] = $user.DisplayName
                    $row["EmailAddress"] = $user.EmailAddress
                    $row["Title"] = $user.Title
                    $row["Department"] = $user.Department
                    $dataTable.Rows.Add($row)
                }
            }
            
            if ($computer) {
                $row = $dataTable.NewRow()
                $row["Type"] = "Computer"
                $row["SamAccountName"] = $computer.SamAccountName
                $row["OU"] = Get-LastOU -distinguishedName $computer.DistinguishedName
                $row["DistinguishedName"] = $computer.DistinguishedName
                $row["OperatingSystem"] = $computer.OperatingSystem
                $row["LastLogonDate"] = $computer.LastLogonDate
                $dataTable.Rows.Add($row)
            }
            
            $resultForm = New-Object System.Windows.Forms.Form
            $resultForm.Text = "Search Results"
            $resultForm.Size = New-Object System.Drawing.Size(800, 400)
            $resultForm.StartPosition = "CenterScreen"
            
            $dataGridView = New-Object System.Windows.Forms.DataGridView
            $dataGridView.Dock = [System.Windows.Forms.DockStyle]::Fill
            $dataGridView.DataSource = $dataTable
            $dataGridView.AutoSizeColumnsMode = [System.Windows.Forms.DataGridViewAutoSizeColumnsMode]::AllCells
            
            $resultForm.Controls.Add($dataGridView)
            $resultForm.ShowDialog() | Out-Null
        } catch {
            [System.Windows.Forms.MessageBox]::Show("An error occurred while searching: $($_.Exception.Message)", "Error", [System.Windows.Forms.MessageBoxButtons]::OK, [System.Windows.Forms.MessageBoxIcon]::Error)
        }
    } else {
        [System.Windows.Forms.MessageBox]::Show("Please enter a search term.", "Error", [System.Windows.Forms.MessageBoxButtons]::OK, [System.Windows.Forms.MessageBoxIcon]::Error)
    }
})

# ========== MOVE OU EVENT HANDLERS ==========

$openFileButton2.Add_Click({
    $result = $openFileDialog2.ShowDialog()
    if ($result -eq [System.Windows.Forms.DialogResult]::OK) {
        $filePathLabel2.Text = $openFileDialog2.FileName
    }
})

# OU Browser Function (from original MoveOU script)
function Show-OUBrowser {
    [CmdletBinding()]
    param ()

    $ouBrowserForm = New-Object System.Windows.Forms.Form
    $ouBrowserForm.Text = "Active Directory OU Browser"
    $ouBrowserForm.Size = New-Object System.Drawing.Size(500, 600)
    $ouBrowserForm.StartPosition = "CenterScreen"

    $treeView = New-Object System.Windows.Forms.TreeView
    $treeView.Dock = [System.Windows.Forms.DockStyle]::Fill
    [void]$ouBrowserForm.Controls.Add($treeView)

    function Populate-TreeView {
        $domain = [System.DirectoryServices.ActiveDirectory.Domain]::GetCurrentDomain()
        $root = $domain.GetDirectoryEntry()
        $rootNode = New-Object System.Windows.Forms.TreeNode($root.Name)
        $rootNode.Tag = [string]$root.distinguishedName
        [void]$treeView.Nodes.Add($rootNode)

        $searcher = New-Object System.DirectoryServices.DirectorySearcher($root)
        $searcher.Filter = "(objectClass=organizationalUnit)"
        $searcher.SearchScope = "Subtree"
        $null = $searcher.PropertiesToLoad.Add("name")
        $null = $searcher.PropertiesToLoad.Add("distinguishedName")

        $nodesByDN = @{ $root.distinguishedName = $rootNode }
        foreach ($result in $searcher.FindAll()) {
            $ou = $result.GetDirectoryEntry()
            $dn = [string]$ou.distinguishedName.Value
            $name = $ou.name.Value
            $node = New-Object System.Windows.Forms.TreeNode($name)
            $node.Tag = $dn
            $parentDN = $dn -replace "^OU=$name,", ""
            if ($nodesByDN.ContainsKey($parentDN)) {
                [void]$nodesByDN[$parentDN].Nodes.Add($node)
            } else {
                [void]$rootNode.Nodes.Add($node)
            }
            $nodesByDN[$dn] = $node
        }
        [void]$rootNode.Expand()
    }

    Populate-TreeView

    $treeView.Add_NodeMouseDoubleClick({
        if ($treeView.SelectedNode) {
            $ouBrowserForm.DialogResult = [System.Windows.Forms.DialogResult]::OK
            $ouBrowserForm.Close()
        }
    })

    $ouBrowserForm.ShowDialog() | Out-Null
    if ($ouBrowserForm.DialogResult -eq [System.Windows.Forms.DialogResult]::OK) {
        return ,([string]$treeView.SelectedNode.Tag)
    }
    return $null
}

$findOUButton2.Add_Click({
    $sel = Show-OUBrowser
    if ($sel) {
        $selectedOULabel2.Text = "Selected Destination OU: $sel"
        $script:selectedOUFullDN = -join $sel
    }
})

# Include the original Move OU Process button logic (condensed)
$processButton2.Add_Click({
    # CLEAR THE GUI CONSOLE BEFORE PROCESSING
    $outputTextBox2.Text = ""
    $outputTextBox2.Refresh()
    
    # Determine export folder: CSV folder if imported, else script directory
    if ($filePathLabel2.Text -ne 'No file selected') {
        $exportBase = Split-Path -Parent $filePathLabel2.Text
    } else {
        $exportBase = $global:ADSuitePaths.Exports
    }

    # Gather objects from manual or CSV
    if ($manualTextBox2.Text) {
        $objects = @($manualTextBox2.Text)
    } elseif ($filePathLabel2.Text -ne 'No file selected') {
        try {
            $csvData = Import-Csv -Path $filePathLabel2.Text
            $objects = $csvData.samaccountname
        } catch {
            $outputTextBox2.Text = "Error reading CSV: $($_.Exception.Message)"
            return
        }
    } else {
        $outputTextBox2.Text = "Please select a CSV file or enter a sAMAccountName."
        return
    }
    
    if (-not $script:selectedOUFullDN) { 
        $outputTextBox2.Text = "Please select a destination OU first."
        return
    }

    $prevList = @()
    $newList  = @()
    $targetDN = $script:selectedOUFullDN
    $output = ""

    foreach ($object in $objects) {
        try {
            $adObj = Get-ADUser -Filter "SamAccountName -eq '$object'" -Properties DistinguishedName -ErrorAction SilentlyContinue
            if (-not $adObj) { $adObj = Get-ADComputer -Filter "SamAccountName -eq '$object$'" -Properties DistinguishedName -ErrorAction SilentlyContinue }
            
            if ($adObj) {
                $prevDN = $adObj.DistinguishedName
                $prevList += [PSCustomObject]@{ samaccountname = $object; location = $prevDN }

                Move-ADObject -Identity $prevDN -TargetPath $targetDN -ErrorAction Stop
                $output += "Moved $object successfully.`r`n"

                $adObjNew = Get-ADUser -Filter "SamAccountName -eq '$object'" -Properties DistinguishedName -ErrorAction SilentlyContinue
                if (-not $adObjNew) { $adObjNew = Get-ADComputer -Filter "SamAccountName -eq '$object$'" -Properties DistinguishedName -ErrorAction SilentlyContinue }
                $newDN = $adObjNew.DistinguishedName
                $newList += [PSCustomObject]@{ samaccountname = $object; isMoved = $newDN }
            } else {
                $output += "Object $object not found, skipping move.`r`n"
            }
        } catch {
            $output += "Error moving $object`: $($_.Exception.Message)`r`n"
        }
    }

    # Export CSVs - APPEND TO EXISTING FILES INSTEAD OF OVERWRITING
    try {
        $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
        
        # Add timestamp to data for tracking
        $prevListWithTime = $prevList | ForEach-Object { 
            $_ | Add-Member -NotePropertyName "Timestamp" -NotePropertyValue $timestamp -PassThru 
        }
        $newListWithTime = $newList | ForEach-Object { 
            $_ | Add-Member -NotePropertyName "Timestamp" -NotePropertyValue $timestamp -PassThru 
        }
        
        $prevPath = Join-Path $exportBase 'previous_ou.csv'
        $newPath = Join-Path $exportBase 'isMoved.csv'
        
        # Check if files exist and append, otherwise create new
        if (Test-Path $prevPath) {
            $prevListWithTime | Export-Csv -Path $prevPath -NoTypeInformation -Append
        } else {
            $prevListWithTime | Export-Csv -Path $prevPath -NoTypeInformation
        }
        
        if (Test-Path $newPath) {
            $newListWithTime | Export-Csv -Path $newPath -NoTypeInformation -Append
        } else {
            $newListWithTime | Export-Csv -Path $newPath -NoTypeInformation
        }
        
        $output += "`r`nExported logs to: $exportBase (APPENDED with timestamp)`r`n"
    } catch {
        $output += "`r`nError exporting logs: $($_.Exception.Message)`r`n"
    }

    $outputTextBox2.Text = $output
})

# Test AD connection on startup
try {
    $domain = [System.DirectoryServices.ActiveDirectory.Domain]::GetCurrentDomain()
    Set-ConnectionStatus "Connected: $($domain.Name)" "Green"
} catch {
    Set-ConnectionStatus "Connection Failed" "Red"
}

# ========== SHOW THE FORM ==========
$global:MainForm.ShowDialog() | Out-Null