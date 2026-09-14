[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)]
    [string]$DistDir,
    [switch]$SkipGuiLaunch,
    [switch]$RequireInteractiveAcceptance
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
if ([Environment]::OSVersion.Platform -ne [PlatformID]::Win32NT) { throw 'Windows build verification must run on Windows.' }
$DistDir = (Resolve-Path $DistDir).Path
$Exe = Join-Path $DistDir 'MMO Video Studio.exe'
$Manifest = Join-Path $DistDir 'build-manifest.json'
foreach ($path in @($Exe,$Manifest,(Join-Path $DistDir 'ui\qml\Main.qml'),(Join-Path $DistDir 'resources\languages.json'),(Join-Path $DistDir 'resources\icons\app.ico'),(Join-Path $DistDir 'bin\ffmpeg.exe'),(Join-Path $DistDir 'bin\ffprobe.exe'),(Join-Path $DistDir 'licenses\THIRD_PARTY_NOTICES.md'),(Join-Path $DistDir 'licenses\ffmpeg\LICENSE.txt'),(Join-Path $DistDir 'licenses\ffmpeg\SOURCE.txt'))) {
    if (-not (Test-Path $path -PathType Leaf)) { throw "Required packaged file missing: $path" }
}

# Verify Qt plugin families without assuming one internal PySide6 folder layout.
$Dlls = Get-ChildItem $DistDir -Recurse -File -Filter '*.dll'
if (-not ($Dlls.Name -contains 'qwindows.dll')) { throw 'Qt Windows platform plugin qwindows.dll is missing.' }
if (-not ($Dlls.Name | Where-Object { $_ -match '^q(jpeg|gif|ico|svg).*\.dll$' })) { throw 'Qt image-format plugin family is missing.' }
if (-not ($Dlls.Name -contains 'Qt6Qml.dll')) { throw 'Qt QML runtime Qt6Qml.dll is missing.' }
if (-not ($Dlls.Name | Where-Object { $_ -match '(ffmpegmedia|windowsmedia).*\.dll$' })) { throw 'Qt Multimedia backend plugin is missing.' }
$QmlCount = (Get-ChildItem (Join-Path $DistDir 'ui\qml') -Recurse -File -Filter '*.qml').Count
if ($QmlCount -lt 10) { throw "QML payload looks incomplete ($QmlCount files)." }

# Development files and obvious secret containers must never be in dist.
$ForbiddenNames = @('.git','.env','.env.local','.env.production','tests','test-results','.pytest_cache')
foreach ($name in $ForbiddenNames) {
    if (Get-ChildItem $DistDir -Recurse -Force -ErrorAction SilentlyContinue | Where-Object { $_.Name -eq $name } | Select-Object -First 1) {
        throw "Forbidden development/secret path found in dist: $name"
    }
}
if (Get-ChildItem $DistDir -Recurse -File -Include '*.pem','*.pfx','*.p12','*.key' | Select-Object -First 1) {
    throw 'Private key/certificate material was found in dist.'
}
$TextExtensions = @('*.json','*.toml','*.ini','*.yaml','*.yml','*.txt','*.md','*.conf','*.cfg')
$CredentialPattern = '(?i)(api[_-]?key|secret[_-]?key|access[_-]?token|authorization)\s*[:=]\s*["'']?[A-Za-z0-9_\-]{20,}'
foreach ($file in Get-ChildItem $DistDir -Recurse -File -Include $TextExtensions -ErrorAction SilentlyContinue) {
    $text = Get-Content $file.FullName -Raw -ErrorAction SilentlyContinue
    if ($text -and $text -match $CredentialPattern) { throw "Possible credential found in packaged text file: $($file.FullName)" }
}

# Copy outside the source tree to a path with spaces + Unicode, use a clean profile,
# remove Python from PATH, and execute the compiled self-check.
$QaRoot = Join-Path $env:TEMP ('MMO Video Studio Phase40 QA ខ្មែរ ' + [Guid]::NewGuid().ToString('N').Substring(0,8))
$QaDist = Join-Path $QaRoot 'Program Files Like\MMO Video Studio'
$ProfileRoot = Join-Path $QaRoot 'Fresh User\AppData\Local'
New-Item -ItemType Directory -Force -Path (Split-Path $QaDist),$ProfileRoot | Out-Null
Copy-Item $DistDir $QaDist -Recurse -Force
$QaExe = Join-Path $QaDist 'MMO Video Studio.exe'
$Report = Join-Path $QaRoot 'self-check.json'
$OldLocal = $env:LOCALAPPDATA; $OldPath = $env:PATH
try {
    $env:LOCALAPPDATA = $ProfileRoot
    $env:PATH = "$env:SystemRoot\System32;$env:SystemRoot"
    $proc = Start-Process -FilePath $QaExe -ArgumentList @('--phase40-self-check', ('"{0}"' -f $Report)) -Wait -PassThru -NoNewWindow
    if ($proc.ExitCode -ne 0) { throw "No-Python packaged self-check failed with exit code $($proc.ExitCode)." }
    if (-not (Test-Path $Report)) { throw 'Packaged self-check report was not created.' }
    $result = Get-Content $Report -Raw | ConvertFrom-Json
    if (-not $result.ok) { throw 'Packaged self-check reported failure.' }
    $expectedRoot = Join-Path $ProfileRoot 'MMOVideoStudio'
    if (-not ([IO.Path]::GetFullPath($result.dataRoot).StartsWith([IO.Path]::GetFullPath($expectedRoot), [StringComparison]::OrdinalIgnoreCase))) {
        throw "Packaged app wrote outside clean LOCALAPPDATA: $($result.dataRoot)"
    }

    if (-not $SkipGuiLaunch) {
        $gui = Start-Process -FilePath $QaExe -PassThru
        Start-Sleep -Seconds 8
        if ($gui.HasExited) { throw "GUI exited during launch/QML smoke with code $($gui.ExitCode)." }
        Stop-Process -Id $gui.Id -Force
    }
} finally {
    $env:LOCALAPPDATA = $OldLocal
    $env:PATH = $OldPath
}

if ($RequireInteractiveAcceptance) {
    Write-Host ''
    Write-Host 'Manual packaged acceptance required:' -ForegroundColor Cyan
    Write-Host '1. Launch Home with the fresh profile.'
    Write-Host '2. Create a project.'
    Write-Host '3. Import a tiny video, preview it, and add overlay text.'
    Write-Host '4. Export with bundled FFmpeg.'
    Write-Host '5. Close/reopen the project.'
    Write-Host '6. Open Diagnostics and confirm no missing resource/plugin errors.'
    Write-Host '7. Open Models with no managed AI models installed and confirm the page works without a crash.'
    $answer = Read-Host 'Type PASS only after all seven steps succeed'
    if ($answer -ne 'PASS') { throw 'Interactive packaged acceptance was not completed.' }
}

Remove-Item $QaRoot -Recurse -Force -ErrorAction SilentlyContinue
Write-Host 'Phase 40 Windows package verification passed.' -ForegroundColor Green
