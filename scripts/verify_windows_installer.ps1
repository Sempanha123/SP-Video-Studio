[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)]
    [string]$Installer,
    [string]$PreviousInstaller = '',
    [switch]$RequireCleanProfile,
    [switch]$RequireNonAdmin,
    [switch]$RequireUpgradeFixture,
    [switch]$RequireInteractiveAcceptance,
    [switch]$SkipGuiLaunch,
    [switch]$SkipOptionalDataRemovalTest
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
if ([Environment]::OSVersion.Platform -ne [PlatformID]::Win32NT) { throw 'Phase 41 installer verification must run on Windows 11 x64.' }
if ([Environment]::Is64BitOperatingSystem -ne $true) { throw 'Windows x64 is required.' }

$Installer = (Resolve-Path $Installer).Path
if (-not [string]::IsNullOrWhiteSpace($PreviousInstaller)) { $PreviousInstaller = (Resolve-Path $PreviousInstaller).Path }
if ($RequireUpgradeFixture -and [string]::IsNullOrWhiteSpace($PreviousInstaller)) { throw '-RequireUpgradeFixture requires -PreviousInstaller from a real earlier release built with the same AppId.' }

if ($RequireNonAdmin) {
    $Identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $Principal = New-Object Security.Principal.WindowsPrincipal($Identity)
    if ($Principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
        throw 'Non-admin acceptance was requested, but this PowerShell process is elevated/administrative.'
    }
}

$HashSidecar = $Installer + '.sha256'
if (-not (Test-Path $HashSidecar -PathType Leaf)) { throw "Installer SHA-256 sidecar is missing: $HashSidecar" }
$ExpectedHash = ((Get-Content $HashSidecar -Raw).Trim() -split '\s+')[0].ToLowerInvariant()
$ActualHash = (Get-FileHash $Installer -Algorithm SHA256).Hash.ToLowerInvariant()
if ($ExpectedHash -ne $ActualHash) { throw 'Installer SHA-256 does not match its sidecar.' }


$UninstallRegistryPath = 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\{38CE0934-A2D4-4D9B-9499-AEA7F28FC0EB}_is1'
$ExistingStartMenu = Join-Path $env:APPDATA 'Microsoft\Windows\Start Menu\Programs\MMO Video Studio\MMO Video Studio.lnk'
if (Test-Path $UninstallRegistryPath) {
    throw 'Phase 41 installer verification refuses to run over an existing MMO Video Studio installation. Use a disposable clean Windows profile/VM.'
}
if (Test-Path $ExistingStartMenu) {
    throw 'Phase 41 installer verification found an existing MMO Video Studio Start Menu shortcut. Use a disposable clean Windows profile/VM.'
}

$DataRoot = Join-Path $env:LOCALAPPDATA 'MMOVideoStudio'
if (Test-Path $DataRoot) {
    throw "Phase 41 installer verification refuses any pre-existing managed data root. Use a disposable clean Windows profile/VM: $DataRoot"
}
$DataRootExistedBefore = $false

$QaId = [Guid]::NewGuid().ToString('N').Substring(0,8)
$QaRoot = Join-Path $env:TEMP ("MMO Video Studio Phase41 QA ខ្មែរ $QaId")
$InstallDir = Join-Path $env:LOCALAPPDATA ("Programs\MMO Video Studio Phase41 QA ខ្មែរ $QaId")
$ExternalProject = Join-Path $QaRoot 'External Projects ខ្មែរ\project.json'
$InstallLog = Join-Path $QaRoot 'install.log'
$UninstallLog = Join-Path $QaRoot 'uninstall.log'
$SelfCheckReport = Join-Path $QaRoot 'self-check.json'
New-Item -ItemType Directory -Force -Path (Split-Path $ExternalProject) | Out-Null
'{"title":"Phase 41 external project sentinel — ខ្មែរ ไทย Tiếng Việt"}' | Set-Content $ExternalProject -Encoding utf8

function Invoke-Setup([string]$SetupPath, [string]$LogPath) {
    $Args = @('/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART',('/DIR="{0}"' -f $InstallDir),('/LOG="{0}"' -f $LogPath))
    $Proc = Start-Process -FilePath $SetupPath -ArgumentList $Args -Wait -PassThru
    if ($Proc.ExitCode -ne 0) { throw "Installer failed with exit code $($Proc.ExitCode): $SetupPath" }
    if (-not (Test-Path $LogPath -PathType Leaf)) { throw "Installer log was not produced: $LogPath" }
}

function Get-Uninstaller() {
    $Item = Get-ChildItem $InstallDir -File -Filter 'unins*.exe' -ErrorAction SilentlyContinue | Sort-Object Name | Select-Object -First 1
    if (-not $Item) { throw "Uninstaller was not found under $InstallDir" }
    return $Item.FullName
}

function Invoke-Uninstall([switch]$RemoveAppData) {
    $Uninstaller = Get-Uninstaller
    $Args = @('/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART',('/LOG="{0}"' -f $UninstallLog))
    if ($RemoveAppData) { $Args += '/REMOVEAPPDATA' }
    $Proc = Start-Process -FilePath $Uninstaller -ArgumentList $Args -Wait -PassThru
    if ($Proc.ExitCode -ne 0) { throw "Uninstaller failed with exit code $($Proc.ExitCode)." }
    Start-Sleep -Milliseconds 700
}

function Write-ManagedSentinels() {
    foreach ($Relative in @('settings','models','assets','templates','cache','recovery','logs','exports')) {
        $Dir = Join-Path $DataRoot $Relative
        New-Item -ItemType Directory -Force -Path $Dir | Out-Null
        ("phase41-$Relative — ខ្មែរ ไทย Tiếng Việt") | Set-Content (Join-Path $Dir 'phase41-preserve.txt') -Encoding utf8
    }
}

function Assert-ManagedSentinels([bool]$ShouldExist) {
    foreach ($Relative in @('settings','models','assets','templates','cache','recovery','logs','exports')) {
        $Path = Join-Path (Join-Path $DataRoot $Relative) 'phase41-preserve.txt'
        if ($ShouldExist -and -not (Test-Path $Path -PathType Leaf)) { throw "Managed data was unexpectedly removed: $Path" }
        if (-not $ShouldExist -and (Test-Path $Path)) { throw "Managed data removal left a QA sentinel behind: $Path" }
    }
}

function Invoke-PackagedSelfCheck() {
    $Exe = Join-Path $InstallDir 'MMO Video Studio.exe'
    if (-not (Test-Path $Exe -PathType Leaf)) { throw "Installed executable missing: $Exe" }
    $OldPath = $env:PATH
    try {
        $env:PATH = "$env:SystemRoot\System32;$env:SystemRoot"
        $Proc = Start-Process -FilePath $Exe -ArgumentList @('--phase40-self-check', ('"{0}"' -f $SelfCheckReport)) -Wait -PassThru -NoNewWindow
        if ($Proc.ExitCode -ne 0) { throw "Installed no-Python/FFmpeg self-check failed with exit code $($Proc.ExitCode)." }
    } finally {
        $env:PATH = $OldPath
    }
    $Payload = Get-Content $SelfCheckReport -Raw | ConvertFrom-Json
    if (-not $Payload.ok) { throw 'Installed package self-check reported failure.' }
}

function Assert-Shortcuts() {
    $StartMenu = Join-Path $env:APPDATA 'Microsoft\Windows\Start Menu\Programs\MMO Video Studio\MMO Video Studio.lnk'
    if (-not (Test-Path $StartMenu -PathType Leaf)) { throw "Start Menu shortcut missing: $StartMenu" }
    $Desktop = Join-Path ([Environment]::GetFolderPath('Desktop')) 'MMO Video Studio.lnk'
    if (Test-Path $Desktop) { throw 'Desktop shortcut should be unchecked by default.' }
}

try {
    # Fresh install on a Unicode/path-with-spaces target.
    Invoke-Setup $Installer $InstallLog
    Assert-Shortcuts
    Invoke-PackagedSelfCheck
    Write-ManagedSentinels

    if (-not $SkipGuiLaunch) {
        $Gui = Start-Process -FilePath (Join-Path $InstallDir 'MMO Video Studio.exe') -PassThru
        Start-Sleep -Seconds 8
        if ($Gui.HasExited) { throw "Installed GUI exited during startup smoke with code $($Gui.ExitCode)." }
        Stop-Process -Id $Gui.Id -Force
    }

    if ($RequireInteractiveAcceptance) {
        Write-Host ''
        Write-Host 'Fresh-install acceptance required from the installed Start Menu shortcut:' -ForegroundColor Cyan
        Write-Host '1. Launch MMO Video Studio from Start Menu.'
        Write-Host '2. Complete or skip onboarding.'
        Write-Host '3. Create a project with Unicode text (Khmer/Thai/Vietnamese is useful).'
        Write-Host '4. Import a tiny media file, render/export with bundled FFmpeg, then close/reopen the project.'
        Write-Host '5. Start the installer again while the app is running and confirm it asks you to close the app instead of force-replacing files.'
        $Answer = Read-Host 'Type PASS after all five fresh-install steps succeed'
        if ($Answer -ne 'PASS') { throw 'Interactive fresh-install acceptance was not completed.' }
    }

    # Default uninstall must preserve every managed-data sentinel and external project.
    Invoke-Uninstall
    if (Test-Path (Join-Path $InstallDir 'MMO Video Studio.exe')) { throw 'Application binary remained after uninstall.' }
    Assert-ManagedSentinels $true
    if (-not (Test-Path $ExternalProject -PathType Leaf)) { throw 'External project was deleted during default uninstall.' }
    $StartMenu = Join-Path $env:APPDATA 'Microsoft\Windows\Start Menu\Programs\MMO Video Studio\MMO Video Studio.lnk'
    if (Test-Path $StartMenu) { throw 'Start Menu shortcut remained after uninstall.' }

    # Explicit managed-data removal is only safe to automate in a clean disposable profile.
    if (-not $SkipOptionalDataRemovalTest) {
        if ($DataRootExistedBefore) {
            throw 'Refusing destructive optional-data-removal test because this was not a clean disposable profile.'
        }
        Invoke-Setup $Installer (Join-Path $QaRoot 'reinstall.log')
        Write-ManagedSentinels
        Invoke-Uninstall -RemoveAppData
        if (Test-Path $DataRoot) { throw "Explicit managed-data removal did not remove $DataRoot" }
        if (-not (Test-Path $ExternalProject -PathType Leaf)) { throw 'Explicit managed-data removal touched an external project.' }
    }

    # Upgrade N -> N+1 and downgrade blocking require a real previous installer fixture.
    if (-not [string]::IsNullOrWhiteSpace($PreviousInstaller)) {
        Invoke-Setup $PreviousInstaller (Join-Path $QaRoot 'previous-install.log')
        Write-ManagedSentinels
        'previous-template' | Set-Content (Join-Path $DataRoot 'templates\phase41-upgrade-template.txt') -Encoding utf8
        'previous-asset' | Set-Content (Join-Path $DataRoot 'assets\phase41-upgrade-asset.txt') -Encoding utf8
        'previous-model-metadata' | Set-Content (Join-Path $DataRoot 'models\phase41-upgrade-model.txt') -Encoding utf8
        Invoke-Setup $Installer (Join-Path $QaRoot 'upgrade.log')
        Assert-ManagedSentinels $true
        foreach ($Path in @(
            (Join-Path $DataRoot 'templates\phase41-upgrade-template.txt'),
            (Join-Path $DataRoot 'assets\phase41-upgrade-asset.txt'),
            (Join-Path $DataRoot 'models\phase41-upgrade-model.txt'),
            $ExternalProject
        )) {
            if (-not (Test-Path $Path -PathType Leaf)) { throw "Upgrade did not preserve fixture data: $Path" }
        }

        if ($RequireInteractiveAcceptance) {
            Write-Host ''
            Write-Host 'Upgrade acceptance required:' -ForegroundColor Cyan
            Write-Host 'Open the previous-version project fixture in the upgraded app and confirm migrations complete, content is preserved, and save/reopen/render still work.'
            $UpgradeAnswer = Read-Host 'Type PASS after the upgrade/migration workflow succeeds'
            if ($UpgradeAnswer -ne 'PASS') { throw 'Interactive upgrade acceptance was not completed.' }
        }

        $Downgrade = Start-Process -FilePath $PreviousInstaller -ArgumentList @('/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART',('/DIR="{0}"' -f $InstallDir),('/LOG="{0}"' -f (Join-Path $QaRoot 'downgrade.log'))) -Wait -PassThru
        if ($Downgrade.ExitCode -eq 0) { throw 'Previous installer unexpectedly succeeded over the newer installed version; downgrade guard failed.' }

        Invoke-Uninstall
        Assert-ManagedSentinels $true
    }

    Write-Host 'Phase 41 Windows installer verification passed.' -ForegroundColor Green
} finally {
    # Never remove a pre-existing user data root. Clean-profile QA data can be cleaned only
    # after the explicit managed-data test has already proven scope safety.
    if (-not $DataRootExistedBefore -and (Test-Path $DataRoot)) {
        Remove-Item $DataRoot -Recurse -Force -ErrorAction SilentlyContinue
    }
    Remove-Item $InstallDir -Recurse -Force -ErrorAction SilentlyContinue
    Remove-Item $QaRoot -Recurse -Force -ErrorAction SilentlyContinue
}
