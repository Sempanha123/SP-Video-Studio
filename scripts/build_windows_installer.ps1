[CmdletBinding()]
param(
    [string]$DistDir = 'dist\MMO Video Studio',
    [string]$OutputDir = 'dist\installer',
    [string]$InnoCompiler = $env:MMOVS_INNO_COMPILER,
    [string]$SigningCertificateThumbprint = $env:MMOVS_SIGN_CERT_THUMBPRINT,
    [string]$SigningTimestampUrl = $env:MMOVS_SIGN_TIMESTAMP_URL,
    [switch]$AllowNewerCompiler,
    [switch]$RunNativeVerify
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
Set-Location $RepoRoot

if ([Environment]::OSVersion.Platform -ne [PlatformID]::Win32NT) { throw 'Phase 41 installer build must run on Windows 11 x64.' }
if ([Environment]::Is64BitOperatingSystem -ne $true) { throw 'Windows x64 is required.' }

$DistDir = (Resolve-Path $DistDir).Path
$ManifestPath = Join-Path $DistDir 'build-manifest.json'
foreach ($required in @(
    (Join-Path $DistDir 'MMO Video Studio.exe'),
    $ManifestPath,
    (Join-Path $DistDir 'bin\ffmpeg.exe'),
    (Join-Path $DistDir 'bin\ffprobe.exe'),
    (Join-Path $DistDir 'licenses\THIRD_PARTY_NOTICES.md'),
    (Join-Path $DistDir 'licenses\ffmpeg\LICENSE.txt'),
    (Join-Path $DistDir 'licenses\ffmpeg\SOURCE.txt')
)) {
    if (-not (Test-Path $required -PathType Leaf)) { throw "Verified Phase 40 distribution file is missing: $required" }
}

$Manifest = Get-Content $ManifestPath -Raw | ConvertFrom-Json
$ConstantsText = Get-Content (Join-Path $RepoRoot 'app\constants.py') -Raw
$VersionMatch = [regex]::Match($ConstantsText, '(?m)^APP_VERSION\s*=\s*["''](?<version>\d+(?:\.\d+){1,3})["'']\s*$')
if (-not $VersionMatch.Success) { throw 'Could not resolve app.constants.APP_VERSION.' }
$Version = $VersionMatch.Groups['version'].Value
if ([string]$Manifest.appVersion -ne $Version) {
    throw "Phase 40 build-manifest version '$($Manifest.appVersion)' does not match central APP_VERSION '$Version'. Rebuild Phase 40 first."
}
$Parts = @($Version.Split('.'))
while ($Parts.Count -lt 4) { $Parts += '0' }
if ($Parts.Count -gt 4) { throw "APP_VERSION has too many numeric components: $Version" }
$VersionQuad = ($Parts[0..3] -join '.')

$Candidates = @()
if (-not [string]::IsNullOrWhiteSpace($InnoCompiler)) { $Candidates += $InnoCompiler }
foreach ($Base in @($env:ProgramFiles, ${env:ProgramFiles(x86)}, $env:LOCALAPPDATA)) {
    if ([string]::IsNullOrWhiteSpace($Base)) { continue }
    if ($Base -eq $env:LOCALAPPDATA) {
        $Candidates += (Join-Path $Base 'Programs\Inno Setup 7\ISCC.exe')
    } else {
        $Candidates += (Join-Path $Base 'Inno Setup 7\ISCC.exe')
    }
}
$Compiler = $Candidates | Where-Object { $_ -and (Test-Path $_ -PathType Leaf) } | Select-Object -First 1
if (-not $Compiler) {
    throw 'Inno Setup 7.1.0 x64 compiler (ISCC.exe) was not found. Install the reviewed compiler or pass -InnoCompiler / MMOVS_INNO_COMPILER. This script does not download it silently.'
}
$Compiler = (Resolve-Path $Compiler).Path
$CompilerVersion = (Get-Item $Compiler).VersionInfo.FileVersion
if (-not $AllowNewerCompiler -and -not $CompilerVersion.StartsWith('7.1.0')) {
    throw "Expected Inno Setup 7.1.0 for the reproducible Phase 41 build; found $CompilerVersion. Pass -AllowNewerCompiler only after reviewing the newer compiler."
}

$BuildRoot = Join-Path $RepoRoot '.build\phase41-installer'
$StageRoot = Join-Path $BuildRoot 'staging'
$StageDist = Join-Path $StageRoot 'MMO Video Studio'
Remove-Item $StageRoot -Recurse -Force -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force -Path $StageRoot | Out-Null
Copy-Item $DistDir $StageDist -Recurse -Force


if ([IO.Path]::IsPathRooted($OutputDir)) {
    $OutputDir = [IO.Path]::GetFullPath($OutputDir)
} else {
    $OutputDir = [IO.Path]::GetFullPath((Join-Path $RepoRoot $OutputDir))
}
New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null
$ExpectedSetup = Join-Path $OutputDir ("MMO-Video-Studio-{0}-Setup.exe" -f $Version)
$ExpectedHash = $ExpectedSetup + '.sha256'
Remove-Item $ExpectedSetup,$ExpectedHash -Force -ErrorAction SilentlyContinue

$Iss = Join-Path $RepoRoot 'packaging\windows\installer\MMO-Video-Studio.iss'
$CompileArgs = @(
    '/Qp',
    ('/DMyAppVersion={0}' -f $Version),
    ('/DMyAppVersionQuad={0}' -f $VersionQuad),
    ('/DMySourceDir={0}' -f $StageDist),
    ('/DMyOutputDir={0}' -f $OutputDir),
    ('/DMyRepoRoot={0}' -f $RepoRoot),
    $Iss
)
Write-Host "Compiling MMO Video Studio $Version per-user installer with Inno Setup $CompilerVersion..."
& $Compiler @CompileArgs
if ($LASTEXITCODE -ne 0) { throw "Inno Setup compiler failed with exit code $LASTEXITCODE." }
if (-not (Test-Path $ExpectedSetup -PathType Leaf)) { throw "Expected installer output was not created: $ExpectedSetup" }

$Signed = $false
if (-not [string]::IsNullOrWhiteSpace($SigningCertificateThumbprint)) {
    $SignToolCommand = Get-Command signtool.exe -ErrorAction SilentlyContinue
    if (-not $SignToolCommand) { throw 'Signing certificate was configured but signtool.exe is unavailable.' }
    $SignArgs = @('sign','/sha1',$SigningCertificateThumbprint,'/fd','SHA256')
    if (-not [string]::IsNullOrWhiteSpace($SigningTimestampUrl)) { $SignArgs += @('/tr',$SigningTimestampUrl,'/td','SHA256') }
    $SignArgs += $ExpectedSetup
    & $SignToolCommand.Source @SignArgs
    if ($LASTEXITCODE -ne 0) { throw 'Installer code signing failed.' }
    $Signed = $true
}

$Hash = (Get-FileHash $ExpectedSetup -Algorithm SHA256).Hash.ToLowerInvariant()
("{0}  {1}" -f $Hash, (Split-Path $ExpectedSetup -Leaf)) | Set-Content -Path $ExpectedHash -Encoding ascii

$InstallerManifest = [ordered]@{
    schemaVersion = 1
    productName = 'MMO Video Studio'
    appVersion = $Version
    appId = '{38CE0934-A2D4-4D9B-9499-AEA7F28FC0EB}'
    installScope = 'per-user'
    defaultInstallRoot = '%LOCALAPPDATA%/Programs/MMO Video Studio'
    userDataRoot = '%LOCALAPPDATA%/MMOVideoStudio'
    innoSetupVersion = $CompilerVersion
    sourceBuildManifest = $ManifestPath
    installer = (Split-Path $ExpectedSetup -Leaf)
    sha256 = $Hash
    signed = $Signed
    buildTimeUtc = [DateTime]::UtcNow.ToString('o')
}
$InstallerManifest | ConvertTo-Json -Depth 4 | Set-Content -Path (Join-Path $OutputDir 'installer-manifest.json') -Encoding utf8

if ($RunNativeVerify) {
    & (Join-Path $RepoRoot 'scripts\verify_windows_installer.ps1') -Installer $ExpectedSetup -RequireCleanProfile
    if ($LASTEXITCODE -ne 0) { throw 'Installer smoke verification failed.' }
}

Write-Host "Installer output: $ExpectedSetup" -ForegroundColor Green
Write-Host "SHA-256: $Hash"
