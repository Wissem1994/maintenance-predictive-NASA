param(
    [ValidateSet('Start', 'Stop')][string]$Action = 'Start',
    [switch]$NoBrowser,
    [ValidateRange(5, 300)][int]$TimeoutSeconds = 90
)

$ErrorActionPreference = 'Stop'
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$StateDirectory = Join-Path $ProjectRoot '.cache\launcher'
$LogDirectory = Join-Path $StateDirectory 'logs'
$StateFile = Join-Path $StateDirectory 'processes.json'
$AppUrl = 'http://localhost:5173'
$State = @{ backend = $null; frontend = $null }
$Started = @()
$Locked = $false
$Mutex = $null
New-Item -ItemType Directory -Force -Path $LogDirectory | Out-Null

function Write-Status([string]$Message) {
    Write-Host $Message
    Add-Content -LiteralPath (Join-Path $LogDirectory 'launcher.log') -Encoding UTF8 `
        -Value ("{0:u} {1}" -f [DateTime]::UtcNow, $Message)
}

function Save-State {
    $State | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $StateFile -Encoding UTF8
}

function Get-OwnedProcess($Record) {
    if ($null -eq $Record) { return $null }
    $Process = Get-Process -Id $Record.Id -ErrorAction SilentlyContinue
    if ($null -eq $Process) { return $null }
    try {
        if ($Process.StartTime.ToUniversalTime().Ticks.ToString() -eq $Record.StartTimeTicks -and
            $Process.Path -eq $Record.Executable) { return $Process }
    } catch { }
    return $null
}

function Test-Ready([string]$Name) {
    try {
        if ($Name -eq 'backend') {
            $Health = Invoke-WebRequest -UseBasicParsing -Uri 'http://127.0.0.1:8000/api/health' -TimeoutSec 2
            $Data = $Health.Content | ConvertFrom-Json
            if ($Data.status -ne 'ok' -or $Data.database -ne 'connected') { return $false }
            $Spec = Invoke-WebRequest -UseBasicParsing -Uri 'http://127.0.0.1:8000/openapi.json' -TimeoutSec 2
            return (($Spec.Content | ConvertFrom-Json).info.title -eq 'PredictMaint AI')
        }
        $Page = Invoke-WebRequest -UseBasicParsing -Uri 'http://127.0.0.1:5173' -TimeoutSec 2
        return ($Page.Content -match '<title>PredictMaint AI' -and $Page.Content -match '/src/main.tsx')
    } catch { return $false }
}

function Test-Port([int]$Port) {
    $Client = New-Object System.Net.Sockets.TcpClient
    try {
        $Task = $Client.ConnectAsync('127.0.0.1', $Port)
        return ($Task.Wait(500) -and $Client.Connected)
    } catch { return $false }
    finally { $Client.Dispose() }
}

function Wait-Ready([string]$Name) {
    $Deadline = [DateTime]::UtcNow.AddSeconds($TimeoutSeconds)
    while ([DateTime]::UtcNow -lt $Deadline) {
        if (Test-Ready $Name) { return }
        if ($null -eq (Get-OwnedProcess $State[$Name])) {
            throw "Le $Name s'est arrete. Consultez $LogDirectory\$Name.err.log et $Name.out.log."
        }
        Start-Sleep -Milliseconds 400
    }
    throw "Le $Name ne repond pas apres $TimeoutSeconds secondes. Consultez $LogDirectory."
}

function Start-Server([string]$Name, [string]$Executable, [string]$Arguments,
                      [string]$WorkingDirectory, [string]$StopFile = '') {
    $Process = Start-Process -FilePath $Executable -ArgumentList $Arguments `
        -WorkingDirectory $WorkingDirectory -WindowStyle Hidden -PassThru `
        -RedirectStandardOutput (Join-Path $LogDirectory "$Name.out.log") `
        -RedirectStandardError (Join-Path $LogDirectory "$Name.err.log")
    $State[$Name] = @{
        Id = $Process.Id
        StartTimeTicks = $Process.StartTime.ToUniversalTime().Ticks.ToString()
        # Process.Path can be temporarily empty immediately after Start-Process.
        Executable = [System.IO.Path]::GetFullPath($Executable)
        StopFile = $StopFile
    }
    $script:Started += $Name
    Save-State
    Write-Status "$Name demarre (PID $($Process.Id))."
    Wait-Ready $Name
}

function Stop-Server([string]$Name) {
    $Record = $State[$Name]
    $Process = Get-OwnedProcess $Record
    if ($null -ne $Process) {
        if ($Name -eq 'backend' -and $Record.StopFile) {
            $StopPath = [System.IO.Path]::GetFullPath($Record.StopFile)
            if ((Split-Path -Parent $StopPath) -ne $StateDirectory -or
                (Split-Path -Leaf $StopPath) -notmatch '^backend-[a-f0-9]{32}\.stop$') {
                throw 'Le fichier de controle du backend est invalide.'
            }
            # The worker asks Uvicorn to finish requests and close the engine/database.
            [System.IO.File]::WriteAllText($StopPath, 'stop')
            $null = $Process.WaitForExit(15000)
        }
        if ($null -ne (Get-OwnedProcess $Record)) {
            # Only the recorded process (PID + creation time + executable) and its children.
            $Result = & "$env:SystemRoot\System32\taskkill.exe" /PID $Record.Id /T /F 2>&1
            if ($LASTEXITCODE -ne 0 -and $null -ne (Get-OwnedProcess $Record)) {
                throw "Impossible d'arreter $Name : $Result"
            }
            $null = $Process.WaitForExit(5000)
            if ($null -ne (Get-OwnedProcess $Record)) { throw "Le $Name fonctionne encore." }
        }
        Write-Status "$Name arrete."
    }
    $State[$Name] = $null
    Save-State
}

try {
    # One lock per project, shared by start and stop, including simultaneous double-clicks.
    $Hasher = [System.Security.Cryptography.SHA256]::Create()
    try {
        $Hash = [BitConverter]::ToString($Hasher.ComputeHash(
            [Text.Encoding]::UTF8.GetBytes($ProjectRoot.ToLowerInvariant()))).Replace('-', '')
    } finally { $Hasher.Dispose() }
    $Mutex = New-Object System.Threading.Mutex($false, "Local\PredictMaint-$Hash")
    try { $Locked = $Mutex.WaitOne(120000) }
    catch [System.Threading.AbandonedMutexException] { $Locked = $true }
    if (-not $Locked) { throw 'Un autre lancement est en cours. Reessayez dans quelques instants.' }

    if (Test-Path -LiteralPath $StateFile) {
        $Saved = Get-Content -Raw -LiteralPath $StateFile | ConvertFrom-Json
        $State.backend = $Saved.backend
        $State.frontend = $Saved.frontend
    }

    if ($Action -eq 'Stop') {
        Stop-Server 'frontend'
        Stop-Server 'backend'
        Write-Status 'Les serveurs demarres par le lanceur sont arretes. Vous pouvez fermer le navigateur.'
        exit 0
    }

    Write-Status 'Demarrage de PredictMaint AI...'
    $Python = Join-Path $ProjectRoot '.venv\Scripts\python.exe'
    $Vite = Join-Path $ProjectRoot 'frontend\node_modules\vite\bin\vite.js'
    foreach ($Name in @('backend', 'frontend')) {
        if (Test-Ready $Name) {
            Write-Status "$Name deja pret : instance reutilisee."
            continue
        }
        if ($null -ne (Get-OwnedProcess $State[$Name])) {
            Write-Status "Attente du $Name deja demarre..."
            Wait-Ready $Name
            continue
        }
        $Port = if ($Name -eq 'backend') { 8000 } else { 5173 }
        if (Test-Port $Port) {
            throw "Le port $Port est occupe par un autre service. Liberez-le puis relancez PredictMaint."
        }
        Write-Status "Demarrage du $Name..."
        if ($Name -eq 'backend') {
            if (-not (Test-Path -LiteralPath $Python)) {
                throw 'Python du projet absent. Executez scripts\setup.cmd puis reessayez.'
            }
            $StopFile = Join-Path $StateDirectory ("backend-{0}.stop" -f [Guid]::NewGuid().ToString('N'))
            Start-Server $Name $Python "-u -m scripts.launch_backend --stop-file `"$StopFile`"" $ProjectRoot $StopFile
        } else {
            $Node = Get-Command node.exe -ErrorAction SilentlyContinue
            if ($null -eq $Node) { throw 'Node.js est absent du PATH. Installez-le puis reessayez.' }
            if (-not (Test-Path -LiteralPath $Vite)) {
                throw 'Dependances web absentes. Executez scripts\setup.cmd puis reessayez.'
            }
            Start-Server $Name $Node.Source "`"$Vite`" --host 127.0.0.1 --port 5173 --strictPort" `
                (Join-Path $ProjectRoot 'frontend')
        }
    }
    Write-Status "PredictMaint est pret : $AppUrl"
    if (-not $NoBrowser) {
        try { Start-Process $AppUrl }
        catch { Write-Status "Ouverture automatique impossible. Ouvrez $AppUrl dans votre navigateur." }
    }
    Write-Status 'Pour tout arreter, utilisez Arreter PredictMaint.cmd ou le raccourci du Bureau.'
} catch {
    Write-Status "ERREUR : $($_.Exception.Message)"
    # Undo only processes created by this invocation; leave reused servers alone.
    if ($Action -eq 'Start') {
        for ($Index = $Started.Count - 1; $Index -ge 0; $Index--) {
            try { Stop-Server $Started[$Index] }
            catch { Write-Status "Arret incomplet : $($_.Exception.Message)" }
        }
    }
    exit 1
} finally {
    if ($Locked) { $Mutex.ReleaseMutex() }
    if ($null -ne $Mutex) { $Mutex.Dispose() }
}
