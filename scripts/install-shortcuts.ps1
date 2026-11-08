param([string]$DesktopPath = [Environment]::GetFolderPath('Desktop'))

$ErrorActionPreference = 'Stop'
$ProjectRoot = Split-Path -Parent $PSScriptRoot
if (-not $DesktopPath -or -not (Test-Path -LiteralPath $DesktopPath -PathType Container)) {
    throw 'Bureau introuvable. Indiquez son chemin avec -DesktopPath.'
}
$Shell = New-Object -ComObject WScript.Shell
foreach ($Item in @(
    @{ Name = 'Lancer PredictMaint'; File = 'Lancer PredictMaint.cmd'; Description = 'Demarrer PredictMaint AI' },
    @{ Name = 'Arreter PredictMaint'; File = 'Arreter PredictMaint.cmd'; Description = 'Arreter les serveurs PredictMaint AI' }
)) {
    $ShortcutPath = Join-Path $DesktopPath ($Item.Name + '.lnk')
    $Target = Join-Path $ProjectRoot $Item.File
    $Shortcut = $Shell.CreateShortcut($ShortcutPath)
    if ((Test-Path -LiteralPath $ShortcutPath) -and $Shortcut.TargetPath -ne $Target) {
        throw "Un autre raccourci existe deja : $ShortcutPath"
    }
    $Shortcut.TargetPath = $Target
    $Shortcut.WorkingDirectory = $ProjectRoot
    $Shortcut.Description = $Item.Description
    $Shortcut.IconLocation = "$env:SystemRoot\System32\shell32.dll,13"
    $Shortcut.Save()
    Write-Host "Raccourci cree : $ShortcutPath"
}
