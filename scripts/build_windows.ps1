[CmdletBinding()]
param(
    [ValidateSet('Development','Release','Debug')]
    [string]$Mode = 'Release',
    [string]$FFmpegDir = $env:MMOVS_FFMPEG_DIR,
    [string]$OutputRoot = 'dist',
    [bool]$IncludeAIRuntime = $true,
    [string]$TorchIndexUrl = 'https://download.pytorch.org/whl/cpu',
    [string]$SigningCertificateThumbprint = $env:MMOVS_SIGN_CERT_THUMBPRINT,
    [string]$SigningTimestampUrl = $env:MMOVS_SIGN_TIMESTAMP_URL,
    [switch]$SkipDependencyInstall,
    [switch]$SkipVerify
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
Set-Location $RepoRoot

if ([Environment]::OSVersion.Platform -ne [PlatformID]::Win32NT) { throw 'Phase 40 Windows build must run on Windows 11 x64.' }
if ([Environment]::Is64BitOperatingSystem -ne $true) { throw 'Windows x64 is required.' }

$BuildRoot = Join-Path $RepoRoot '.build\phase40-windows'
$VenvRoot = Join-Path $BuildRoot 'py311'
$Python = Join-Path $VenvRoot 'Scripts\python.exe'
$NuitkaOut = Join-Path $BuildRoot ('nuitka-' + $Mode.ToLowerInvariant())
$FinalRoot = Join-Path $RepoRoot $OutputRoot
$FinalDist = Join-Path $FinalRoot 'MMO Video Studio'
$ConstraintFile = Join-Path $RepoRoot 'packaging\windows\constraints-win311.txt'
$IconFile = Join-Path $RepoRoot 'resources\icons\app.ico'

if (-not (Test-Path $Python)) {
    & py -3.11 -c "import sys,platform; assert sys.version_info[:2]==(3,11); assert platform.architecture()[0]=='64bit'"
    if ($LASTEXITCODE -ne 0) { throw 'CPython 3.11 x64 is required. Install it and retry.' }
    New-Item -ItemType Directory -Force -Path $BuildRoot | Out-Null
    & py -3.11 -m venv $VenvRoot
    if ($LASTEXITCODE -ne 0) { throw 'Could not create the Python 3.11 build environment.' }
}

& $Python -c "import sys,platform; assert sys.version_info[:2]==(3,11), sys.version; assert platform.architecture()[0]=='64bit'"
if ($LASTEXITCODE -ne 0) { throw 'Build environment is not CPython 3.11 x64.' }

if (-not $SkipDependencyInstall) {
    & $Python -m pip install --disable-pip-version-check --upgrade 'pip<27'
    if ($LASTEXITCODE -ne 0) { throw 'pip bootstrap failed.' }
    if ($IncludeAIRuntime) {
        # CPU is the reproducible baseline. A separately reviewed CUDA build may pass another index URL.
        & $Python -m pip install --disable-pip-version-check --index-url $TorchIndexUrl 'torch==2.10.0'
        if ($LASTEXITCODE -ne 0) { throw 'CPU PyTorch runtime installation failed.' }
        & $Python -m pip install --disable-pip-version-check -c $ConstraintFile '.[ai,tts,translation]' 'Nuitka==4.2.1'
    } else {
        & $Python -m pip install --disable-pip-version-check -c $ConstraintFile '.' 'Nuitka==4.2.1'
    }
    if ($LASTEXITCODE -ne 0) { throw 'Pinned Windows build dependencies failed to install.' }
}

& $Python -c "import PySide6, nuitka, sys; from app.constants import APP_VERSION; print('build',sys.version.split()[0],PySide6.__version__,APP_VERSION)"
if ($LASTEXITCODE -ne 0) { throw 'Build dependency validation failed.' }
if ($IncludeAIRuntime) {
    & $Python -c "import ctranslate2, faster_whisper, sentencepiece, soundfile, torch, transformers, voxcpm; print('AI runtime imports OK; torch CUDA available:', torch.cuda.is_available())"
    if ($LASTEXITCODE -ne 0) { throw 'Optional AI runtime import smoke failed before packaging.' }
}

if ([string]::IsNullOrWhiteSpace($FFmpegDir)) { throw 'Provide -FFmpegDir or MMOVS_FFMPEG_DIR. Phase 40 does not download FFmpeg automatically.' }
$FFmpegDir = (Resolve-Path $FFmpegDir).Path
foreach ($name in @('ffmpeg.exe','ffprobe.exe','LICENSE.txt','SOURCE.txt')) {
    if (-not (Test-Path (Join-Path $FFmpegDir $name) -PathType Leaf)) { throw "FFmpeg staging file is missing: $name" }
}
& (Join-Path $FFmpegDir 'ffmpeg.exe') -version | Select-Object -First 1
if ($LASTEXITCODE -ne 0) { throw 'Staged ffmpeg.exe is not runnable.' }
& (Join-Path $FFmpegDir 'ffprobe.exe') -version | Select-Object -First 1
if ($LASTEXITCODE -ne 0) { throw 'Staged ffprobe.exe is not runnable.' }

Remove-Item $NuitkaOut -Recurse -Force -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force -Path $NuitkaOut | Out-Null
$Version = (& $Python -c "from app.constants import APP_VERSION; print(APP_VERSION)").Trim()
$NumericVersion = (($Version -split '\.') + @('0','0','0','0'))[0..3] -join '.'

$NuitkaArgs = @(
    '-m','nuitka',
    '--mode=standalone',
    '--enable-plugin=pyside6',
    '--include-qt-plugins=qml',
    '--include-data-dir=ui/qml=ui/qml',
    '--include-data-dir=resources=resources',
    '--include-data-dir=packaging/windows/notices=licenses',
    '--nofollow-import-to=*.tests',
    '--windows-icon-from-ico=' + $IconFile,
    '--product-name=MMO Video Studio',
    '--company-name=SP Video Studio',
    '--file-description=MMO Video Studio',
    '--copyright=Copyright (c) SP Video Studio',
    '--file-version=' + $NumericVersion,
    '--product-version=' + $NumericVersion,
    '--output-filename=MMO Video Studio.exe',
    '--output-dir=' + $NuitkaOut,
    '--msvc=latest',
    'main.py'
)
if ($Mode -eq 'Release') {
    $NuitkaArgs = $NuitkaArgs[0..($NuitkaArgs.Count-2)] + @('--windows-console-mode=disable') + $NuitkaArgs[-1]
} elseif ($Mode -eq 'Debug') {
    $NuitkaArgs = $NuitkaArgs[0..($NuitkaArgs.Count-2)] + @('--debug','--windows-console-mode=force') + $NuitkaArgs[-1]
} else {
    $NuitkaArgs = $NuitkaArgs[0..($NuitkaArgs.Count-2)] + @('--windows-console-mode=force') + $NuitkaArgs[-1]
}
if ($IncludeAIRuntime) {
    foreach ($pkg in @('faster_whisper','ctranslate2','voxcpm','transformers','torch','sentencepiece','soundfile')) {
        $NuitkaArgs = $NuitkaArgs[0..($NuitkaArgs.Count-2)] + @('--include-package=' + $pkg) + $NuitkaArgs[-1]
    }
}

Write-Host "Building $Mode standalone folder with Python 3.11..."
& $Python @NuitkaArgs
if ($LASTEXITCODE -ne 0) { throw 'Nuitka build failed.' }

$BuiltDist = Get-ChildItem $NuitkaOut -Directory -Filter '*.dist' | Select-Object -First 1
if (-not $BuiltDist) { throw 'Nuitka standalone output directory was not found.' }
Remove-Item $FinalDist -Recurse -Force -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force -Path $FinalRoot | Out-Null
Copy-Item $BuiltDist.FullName $FinalDist -Recurse -Force

$Bin = Join-Path $FinalDist 'bin'
$FFLicense = Join-Path $FinalDist 'licenses\ffmpeg'
New-Item -ItemType Directory -Force -Path $Bin,$FFLicense | Out-Null
Copy-Item (Join-Path $FFmpegDir 'ffmpeg.exe') (Join-Path $Bin 'ffmpeg.exe') -Force
Copy-Item (Join-Path $FFmpegDir 'ffprobe.exe') (Join-Path $Bin 'ffprobe.exe') -Force
Copy-Item (Join-Path $FFmpegDir 'LICENSE.txt') (Join-Path $FFLicense 'LICENSE.txt') -Force
Copy-Item (Join-Path $FFmpegDir 'SOURCE.txt') (Join-Path $FFLicense 'SOURCE.txt') -Force

& $Python scripts\generate_build_manifest.py --dist $FinalDist --mode $Mode --repo $RepoRoot --ffmpeg-source-file (Join-Path $FFmpegDir 'SOURCE.txt')
if ($LASTEXITCODE -ne 0) { throw 'Build manifest generation failed.' }

if (-not [string]::IsNullOrWhiteSpace($SigningCertificateThumbprint)) {
    $SignTool = (Get-Command signtool.exe -ErrorAction SilentlyContinue).Source
    if (-not $SignTool) { throw 'Signing certificate was configured but signtool.exe is unavailable.' }
    $SignArgs = @('sign','/sha1',$SigningCertificateThumbprint,'/fd','SHA256')
    if (-not [string]::IsNullOrWhiteSpace($SigningTimestampUrl)) { $SignArgs += @('/tr',$SigningTimestampUrl,'/td','SHA256') }
    $SignArgs += (Join-Path $FinalDist 'MMO Video Studio.exe')
    & $SignTool @SignArgs
    if ($LASTEXITCODE -ne 0) { throw 'Code signing failed.' }
}

if (-not $SkipVerify) {
    & (Join-Path $RepoRoot 'scripts\verify_windows_build.ps1') -DistDir $FinalDist
    if ($LASTEXITCODE -ne 0) { throw 'Packaged build verification failed.' }
}

Write-Host "Build output: $FinalDist"
