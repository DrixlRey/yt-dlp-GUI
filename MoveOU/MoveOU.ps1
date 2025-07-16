Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.DirectoryServices

# --- Determine Script Directory for Exports ---
# Use PSScriptRoot if available, fall back to MyInvocation or current location.
$scriptDir = if ($PSCommandPath) {
    Split-Path -Parent $PSCommandPath
} elseif ($PSScriptRoot) {
    $PSScriptRoot
} elseif ($MyInvocation.MyCommand.Path) {
    Split-Path -Parent $MyInvocation.MyCommand.Path
} else {
    (Get-Location).Path
}

# --- Main Form ---
$form = New-Object System.Windows.Forms.Form
$form.Text = "MoveOU v5.2"
$form.Size = New-Object System.Drawing.Size(700, 500)
$form.StartPosition = "CenterScreen"

# --- File Path Label ---
$filePathLabel = New-Object System.Windows.Forms.Label
$filePathLabel.Location = New-Object System.Drawing.Point(10, 20)
$filePathLabel.Size = New-Object System.Drawing.Size(660, 20)
$filePathLabel.Text = "No file selected"

# --- Browse Button ---
$openFileButton = New-Object System.Windows.Forms.Button
$openFileButton.Location = New-Object System.Drawing.Point(10, 50)
$openFileButton.Size = New-Object System.Drawing.Size(75, 25)
$openFileButton.Text = "Browse"

$openFileDialog = New-Object System.Windows.Forms.OpenFileDialog
$openFileDialog.Filter = "CSV files (*.csv)|*.csv"
$openFileDialog.Title = "Select a CSV File"

# --- Manual sAMAccountName Label ---
$manualLabel = New-Object System.Windows.Forms.Label
$manualLabel.Location = New-Object System.Drawing.Point(10, 85)
$manualLabel.Size = New-Object System.Drawing.Size(300, 20)
$manualLabel.Text = "Single sAMAccountName (optional):"

# --- Manual sAMAccountName TextBox ---
$manualTextBox = New-Object System.Windows.Forms.TextBox
$manualTextBox.Location = New-Object System.Drawing.Point(10, 110)
$manualTextBox.Size = New-Object System.Drawing.Size(400, 20)

# --- Find Destination OU Button ---
$findOUButton = New-Object System.Windows.Forms.Button
$findOUButton.Location = New-Object System.Drawing.Point(10, 150)
$findOUButton.Size = New-Object System.Drawing.Size(150, 25)
$findOUButton.Text = "Find Destination OU"

# --- Selected Destination OU Label ---
$selectedOULabel = New-Object System.Windows.Forms.TextBox
$selectedOULabel.Location = New-Object System.Drawing.Point(170, 155)
$selectedOULabel.Size = New-Object System.Drawing.Size(520, 20)
$selectedOULabel.ReadOnly = $true
$selectedOULabel.BorderStyle = 'None'
$selectedOULabel.ScrollBars = 'Horizontal'
$selectedOULabel.Text = "No Destination OU selected"

# --- Process Button ---
$processButton = New-Object System.Windows.Forms.Button
$processButton.Location = New-Object System.Drawing.Point(10, 190)
$processButton.Size = New-Object System.Drawing.Size(75, 25)
$processButton.Text = "Process"

# --- Output TextBox ---
$outputTextBox = New-Object System.Windows.Forms.TextBox
$outputTextBox.Location = New-Object System.Drawing.Point(10, 230)
$outputTextBox.Size = New-Object System.Drawing.Size(660, 260)
$outputTextBox.Multiline = $true
$outputTextBox.ScrollBars = [System.Windows.Forms.ScrollBars]::Vertical
$outputTextBox.ReadOnly = $true

# --- Add Controls ---
[void]$form.Controls.Add($filePathLabel)
[void]$form.Controls.Add($openFileButton)
[void]$form.Controls.Add($manualLabel)
[void]$form.Controls.Add($manualTextBox)
[void]$form.Controls.Add($findOUButton)
[void]$form.Controls.Add($selectedOULabel)
[void]$form.Controls.Add($processButton)
[void]$form.Controls.Add($outputTextBox)

# --- Browse Button Event ---
$openFileButton.Add_Click({
    $result = $openFileDialog.ShowDialog()
    if ($result -eq [System.Windows.Forms.DialogResult]::OK) {
        $filePathLabel.Text = $openFileDialog.FileName
    }
})

# --- OU Browser Function ---
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

# --- Find Destination OU Button Event ---
$findOUButton.Add_Click({
    $sel = Show-OUBrowser
    if ($sel) {
        $selectedOULabel.Text = "Selected Destination OU: $sel"
        $script:selectedOUFullDN = -join $sel
    }
})

# --- Process Button Event ---
$processButton.Add_Click({
    # Determine export folder: CSV folder if imported, else script directory
    if ($filePathLabel.Text -ne 'No file selected') {
        $exportBase = Split-Path -Parent $filePathLabel.Text
    } else {
        $exportBase = $scriptDir
    }

    # Gather objects from manual or CSV
    if ($manualTextBox.Text) {
        $objects = @($manualTextBox.Text)
    } elseif ($filePathLabel.Text -ne 'No file selected') {
        $csvData = Import-Csv -Path $filePathLabel.Text
        $objects = $csvData.samaccountname
    } else {
        return
    }
    if (-not $script:selectedOUFullDN) { return }

    $prevList = @()
    $newList  = @()
    $targetDN = $script:selectedOUFullDN

    foreach ($object in $objects) {
        $adObj = Get-ADUser -Filter "SamAccountName -eq '$object'" -Properties DistinguishedName -ErrorAction SilentlyContinue
        if (-not $adObj) { $adObj = Get-ADComputer -Filter "SamAccountName -eq '$object$'" -Properties DistinguishedName -ErrorAction SilentlyContinue }
        $prevDN = $adObj.DistinguishedName
        $prevList += [PSCustomObject]@{ samaccountname = $object; location = $prevDN }

        if ($prevDN) {
            Move-ADObject -Identity $prevDN -TargetPath $targetDN
        } else {
            $outputTextBox.Text += "Object $object not found, skipping move.`n"
        }

        $adObjNew = Get-ADUser -Filter "SamAccountName -eq '$object'" -Properties DistinguishedName -ErrorAction SilentlyContinue
        if (-not $adObjNew) { $adObjNew = Get-ADComputer -Filter "SamAccountName -eq '$object$'" -Properties DistinguishedName -ErrorAction SilentlyContinue }
        $newDN = $adObjNew.DistinguishedName
        $newList  += [PSCustomObject]@{ samaccountname = $object; isMoved = $newDN }
    }

    # Export CSVs
    $prevList | Export-Csv -Path (Join-Path $exportBase 'previous_ou.csv') -NoTypeInformation
    $newList  | Export-Csv -Path (Join-Path $exportBase 'isMoved.csv')      -NoTypeInformation

    $outputTextBox.Text = "Exported logs to: $exportBase`n`n" + ($newList | Out-String)
})

$form.ShowDialog() | Out-Null
