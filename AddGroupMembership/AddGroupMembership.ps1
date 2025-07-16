Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

# Define the group names
$groupNames = @(
"AD-CDCR-Units-PCsRestrictedGroups-Filter",
"App-CDCR-O365Licensing-Project",
"App-CDCR-O365Licensing-Visio",
"App-CDCR-SCCM-ChromeDevelopers",
"App-CDCR-SCCM-M365-Access",
"Share-CDCR-EIS-SAN2-RDCALC-M"
)

# Create the form
$form = New-Object System.Windows.Forms.Form
$form.Text = "Add-GroupMember"
$form.Size = New-Object System.Drawing.Size(500, 520)
$form.StartPosition = "CenterScreen"

# Create the OpenFileDialog
$openFileDialog = New-Object System.Windows.Forms.OpenFileDialog
$openFileDialog.Filter = "CSV files (*.csv)|*.csv"
$openFileDialog.Title = "Select a CSV File"

# Create a label for the file path
$filePathLabel = New-Object System.Windows.Forms.Label
$filePathLabel.Location = New-Object System.Drawing.Point(10, 20)
$filePathLabel.Size = New-Object System.Drawing.Size(320, 20)
$filePathLabel.Text = "No file selected"

# Create a button to open the file dialog
$openFileButton = New-Object System.Windows.Forms.Button
$openFileButton.Location = New-Object System.Drawing.Point(10, 50)
$openFileButton.Size = New-Object System.Drawing.Size(75, 25)
$openFileButton.Text = "Browse"

# Create a label for the sAMAccountName input on top of the TextBox
$manualTextBoxLabel = New-Object System.Windows.Forms.Label
$manualTextBoxLabel.Location = New-Object System.Drawing.Point(10, 85)  # Positioned under the Browse button
$manualTextBoxLabel.Size = New-Object System.Drawing.Size(150, 20)
$manualTextBoxLabel.Text = "Enter sAMAccountName"

# Create a TextBox for manual SamAccountName input, aligned under the label
$manualTextBox = New-Object System.Windows.Forms.TextBox
$manualTextBox.Location = New-Object System.Drawing.Point(10, 110)  # Positioned below the label
$manualTextBox.Size = New-Object System.Drawing.Size(320, 20)
$manualTextBox.Text = ""  # Start off as blank

# Create a label for the groupComboBox
$groupComboBoxLabel = New-Object System.Windows.Forms.Label
$groupComboBoxLabel.Location = New-Object System.Drawing.Point(10, 140)  # Positioned under the sAMAccountName TextBox
$groupComboBoxLabel.Size = New-Object System.Drawing.Size(200, 20)
$groupComboBoxLabel.Text = "Choose group membership"

# Create an extra label to display the container type, manually positioned
$containerLabel = New-Object System.Windows.Forms.Label
$containerLabel.Location = New-Object System.Drawing.Point(95, 200)
$containerLabel.Size = New-Object System.Drawing.Size(160, 20)
$containerLabel.Text = ""  # Initially blank

# Create a combo box for group selection
$groupComboBox = New-Object System.Windows.Forms.ComboBox
$groupComboBox.Location = New-Object System.Drawing.Point(10, 165)  # Positioned under the groupComboBoxLabel
$groupComboBox.Size = New-Object System.Drawing.Size(460, 20)
$groupComboBox.Items.AddRange($groupNames)

# Create a button to process the CSV and manual input
$processButton = New-Object System.Windows.Forms.Button
$processButton.Location = New-Object System.Drawing.Point(10, 195)
$processButton.Size = New-Object System.Drawing.Size(75, 25)
$processButton.Text = "Process"

# Create a TextBox to display the output
$outputTextBox = New-Object System.Windows.Forms.TextBox
$outputTextBox.Location = New-Object System.Drawing.Point(10, 230)
$outputTextBox.Size = New-Object System.Drawing.Size(460, 200)
$outputTextBox.Multiline = $true
$outputTextBox.ScrollBars = [System.Windows.Forms.ScrollBars]::Vertical
$outputTextBox.ReadOnly = $true

# Create a TextBox for search input
$searchTextBox = New-Object System.Windows.Forms.TextBox
$searchTextBox.Location = New-Object System.Drawing.Point(10, 440)
$searchTextBox.Size = New-Object System.Drawing.Size(360, 20)

# Create a button for search
$searchButton = New-Object System.Windows.Forms.Button
$searchButton.Location = New-Object System.Drawing.Point(380, 438)
$searchButton.Size = New-Object System.Drawing.Size(90, 25)
$searchButton.Text = "Search"

# Add controls to the form
$form.Controls.Add($filePathLabel)
$form.Controls.Add($openFileButton)
$form.Controls.Add($manualTextBoxLabel)
$form.Controls.Add($manualTextBox)
$form.Controls.Add($groupComboBoxLabel)
$form.Controls.Add($containerLabel)
$form.Controls.Add($groupComboBox)
$form.Controls.Add($processButton)
$form.Controls.Add($outputTextBox)
$form.Controls.Add($searchTextBox)
$form.Controls.Add($searchButton)

# Define the OpenFileDialog button click event
$openFileButton.Add_Click({
    $result = $openFileDialog.ShowDialog()
    if ($result -eq [System.Windows.Forms.DialogResult]::OK) {
        $filePathLabel.Text = $openFileDialog.FileName
    }
})

# Define the text for when 
$groupComboBox.Add_SelectedIndexChanged({
    $selectedGroup = $groupComboBox.SelectedItem
    switch ($selectedGroup) {
        "App-CDCR-SCCM-ChromeDevelopers" {$containerLabel.Text = "(Computer container)"}
        "AD-CDCR-Units-PCsRestrictedGroups-Filter" { $containerLabel.Text = "(User container)" }
        "App-CDCR-O365Licensing-Project"           { $containerLabel.Text = "(User container)" }
        "App-CDCR-O365Licensing-Visio"               { $containerLabel.Text = "(User container)" }
        "App-CDCR-SCCM-M365-Access"                  { $containerLabel.Text = "(Computer container)" }
        "Share-CDCR-EIS-SAN2-RDCALC-M"               { $containerLabel.Text = "(User container)" }
        Default                                      { $containerLabel.Text = "" }
    }
})

# Define the Process button click event
$processButton.Add_Click({
    $output = ""

    # Check if both CSV file and manual input are empty, and no group is selected
    if ($filePathLabel.Text -eq "No file selected" -and $manualTextBox.Text -eq "" -and $groupComboBox.SelectedItem -eq $null) {
        [System.Windows.Forms.MessageBox]::Show("Please select a CSV file with sAMAccountName list or manually enter one in the box, and a group membership.", "Error", [System.Windows.Forms.MessageBoxButtons]::OK, [System.Windows.Forms.MessageBoxIcon]::Error)
        return
    }

    # Check if CSV file and manual input are both empty but group is selected
    if ($filePathLabel.Text -eq "No file selected" -and $manualTextBox.Text -eq "") {
        [System.Windows.Forms.MessageBox]::Show("Please select a CSV file with sAMAccountName list or manually enter one in the box.", "Error", [System.Windows.Forms.MessageBoxButtons]::OK, [System.Windows.Forms.MessageBoxIcon]::Error)
        return
    }

    # Check if no group is selected
    if ($groupComboBox.SelectedItem -eq $null) {
        [System.Windows.Forms.MessageBox]::Show("Please select a group membership.", "Error", [System.Windows.Forms.MessageBoxButtons]::OK, [System.Windows.Forms.MessageBoxIcon]::Error)
        return
    }

    # If CSV file is selected, process it
    if ($filePathLabel.Text -ne "No file selected") {
        $csvData = Import-Csv -Path $filePathLabel.Text
        $groupName = $groupComboBox.SelectedItem

        foreach ($row in $csvData) {
            $accountName = $row.samaccountname
            try {
                # Try to get the user object
                $objectDN = (Get-ADUser -Filter "SamAccountName -eq '$accountName'" -Properties DistinguishedName).DistinguishedName
                if (-not $objectDN) {
                    # If still not found, try with a trailing '$' for computer accounts
                    $objectDN = (Get-ADComputer -Filter "SamAccountName -eq '$accountName$'" -Properties DistinguishedName).DistinguishedName
                }
                if ($objectDN) {
                    Add-ADGroupMember -Identity $groupName -Members $objectDN
                    if ($output -ne "") {
    $output += "`r`n"
}
if ($output -ne "") {
    $output += "`r`n"
}
$output += "Successfully added $accountName to $groupName.`r`n"
                } else {
                    $output += "Account $accountName not found as user or computer.`n"
                }
                # isMember check
                $groupMembers = Get-ADGroupMember -Identity $groupName -ErrorAction SilentlyContinue
                $isMember = $false
                foreach ($memberObj in $groupMembers) {
                    # Check if the member's SamAccountName matches the input account name (with or without trailing $)
                    if ($memberObj.SamAccountName -eq $accountName -or $memberObj.SamAccountName -eq "$accountName`$") {
                        $isMember = $true
                        break
                    }
                }
                if ($objectDN) {
                    if ($isMember) {
                        $output += "isMember Check: $accountName is now in $groupName`n"
                    } else {
                        $output += "isMember Check: $accountName is NOT in $groupName`n"
                    }
                }
            } catch {
                $errorMessage = $_.Exception.Message
                $errorDetail = $_ | Out-String
                $output += "Error Detail: $errorDetail`n" # Add detailed error information
                $output += "An error occurred while adding $accountName to $groupName. Error: $errorMessage`n"
            }
        }
        # Display the output in the main form's TextBox
        $outputTextBox.Text = $output
        return
    }

    # If no CSV file but manual input is provided, process it
    if ($manualTextBox.Text -ne "") {
        $accountName = $manualTextBox.Text.Trim()
        $groupName = $groupComboBox.SelectedItem
        try {
            # Try to get the user object
            $objectDN = (Get-ADUser -Filter "SamAccountName -eq '$accountName'" -Properties DistinguishedName).DistinguishedName
            if (-not $objectDN) {
                # If still not found, try with a trailing '$' for computer accounts
                $objectDN = (Get-ADComputer -Filter "SamAccountName -eq '$accountName$'" -Properties DistinguishedName).DistinguishedName
            }
            if ($objectDN) {
                Add-ADGroupMember -Identity $groupName -Members $objectDN
                $output += "Successfully added $accountName to $groupName.`n"
            } else {
                $output += "Account $accountName not found as user or computer.`n"
            }
            # isMember check for manual input
            $groupMembers = Get-ADGroupMember -Identity $groupName -ErrorAction SilentlyContinue
            $isMember = $false
            foreach ($memberObj in $groupMembers) {
                # Check if the member's SamAccountName matches the input account name (with or without trailing $)
                if ($memberObj.SamAccountName -eq $accountName -or $memberObj.SamAccountName -eq "$accountName`$") {
                    $isMember = $true
                    break
                }
            }
            $output += "`r`n"
            if ($isMember) {
                $output += "isMember Check: $accountName is now in $groupName`n"
                Write-Host "`nisMember Check: $accountName is now in $groupName"
            } else {
                $output += "isMember Check: $accountName is NOT in $groupName`n"
                Write-Host "`nisMember Check: $accountName is NOT in $groupName"
            }
        } catch {
            $errorMessage = $_.Exception.Message
            $errorDetail = $_ | Out-String
            $output += "Error Detail: $errorDetail`n" # Add detailed error information
            $output += "An error occurred while adding $accountName to $groupName. Error: $errorMessage`n"
        }
        # Display the output in the main form's TextBox
        $outputTextBox.Text = $output
    }
})

# Define the Search button click event
$searchButton.Add_Click({
    $searchTerm = $searchTextBox.Text.Trim()
    if ($searchTerm -ne "") {
        try {
            # Split the search term into parts based on spaces or periods
            $nameParts = $searchTerm -split "[\s.]+" 
            # Build the filter string for flexible searching
            if ($nameParts.Count -eq 1) {
                # Single term: search in GivenName, Surname, or sAMAccountName
                $filter = "GivenName -like '*$searchTerm*' -or Surname -like '*$searchTerm*' -or SamAccountName -like '*$searchTerm*'"
            } elseif ($nameParts.Count -ge 2) {
                # Multiple terms: search combinations in GivenName, Surname, and sAMAccountName
                $filter = @"
(GivenName -like '*$($nameParts[0])*' -and Surname -like '*$($nameParts[1])*') 
-or (GivenName -like '*$($nameParts[1])*' -and Surname -like '*$($nameParts[0])*') 
-or (SamAccountName -like '*$($nameParts[0]).$($nameParts[1])*')
"@
            }
            # Perform the search with the constructed filter
            $users = Get-ADUser -Filter $filter -Properties * -ErrorAction SilentlyContinue
            $computer = Get-ADComputer -Filter "SamAccountName -eq '$searchTerm$'" -Properties * -ErrorAction SilentlyContinue
            # Create a DataTable to hold the search results
            $dataTable = New-Object System.Data.DataTable
            $dataTable.Columns.Add("Type")
            $dataTable.Columns.Add("SamAccountName")
            $dataTable.Columns.Add("OU")  # New column for the last OU
            $dataTable.Columns.Add("DistinguishedName")
            $dataTable.Columns.Add("DisplayName")
            $dataTable.Columns.Add("EmailAddress")
            $dataTable.Columns.Add("Title")
            $dataTable.Columns.Add("Department")
            $dataTable.Columns.Add("OperatingSystem")
            $dataTable.Columns.Add("LastLogonDate")
            # Function to extract the last OU from DistinguishedName
            function Get-LastOU {
                param (
                    [string]$distinguishedName
                )
                $ouParts = $distinguishedName -split ','
                $lastOU = $ouParts | Where-Object { $_ -like 'OU=*' } | Select-Object -Last 1
                return ($lastOU -replace '^OU=', '').Trim()
            }
            # Populate the DataTable with user data
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
            # Populate the DataTable with computer data if found
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
            # Create a new form to display the DataGridView
            $resultForm = New-Object System.Windows.Forms.Form
            $resultForm.Text = "Search Results"
            $resultForm.Size = New-Object System.Drawing.Size(800, 400)
            $resultForm.StartPosition = "CenterScreen"
            # Create a DataGridView to display the DataTable
            $dataGridView = New-Object System.Windows.Forms.DataGridView
            $dataGridView.Dock = [System.Windows.Forms.DockStyle]::Fill
            $dataGridView.DataSource = $dataTable
            # Set the AutoSizeColumnsMode to AllCells for all columns
            $dataGridView.AutoSizeColumnsMode = [System.Windows.Forms.DataGridViewAutoSizeColumnsMode]::AllCells
            # Add the DataGridView to the result form
            $resultForm.Controls.Add($dataGridView)
            # Show the result form as a dialog
            $resultForm.ShowDialog() | Out-Null
        } catch {
            $errorMessage = $_.Exception.Message
            [System.Windows.Forms.MessageBox]::Show("An error occurred while searching: $errorMessage", "Error", [System.Windows.Forms.MessageBoxButtons]::OK, [System.Windows.Forms.MessageBoxIcon]::Error)
        }
    } else {
        [System.Windows.Forms.MessageBox]::Show("Please enter a search term.", "Error", [System.Windows.Forms.MessageBoxButtons]::OK, [System.Windows.Forms.MessageBoxIcon]::Error)
    }
})

# Show the form
$form.ShowDialog() | Out-Null
