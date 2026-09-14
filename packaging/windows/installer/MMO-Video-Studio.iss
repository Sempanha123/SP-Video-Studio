#ifndef MyAppVersion
  #error MyAppVersion must be supplied by scripts/build_windows_installer.ps1
#endif
#ifndef MyAppVersionQuad
  #error MyAppVersionQuad must be supplied by scripts/build_windows_installer.ps1
#endif
#ifndef MySourceDir
  #error MySourceDir must point to the verified Phase 40 standalone folder
#endif
#ifndef MyOutputDir
  #error MyOutputDir must be supplied by scripts/build_windows_installer.ps1
#endif
#ifndef MyRepoRoot
  #error MyRepoRoot must be supplied by scripts/build_windows_installer.ps1
#endif

#define MyAppName "MMO Video Studio"
#define MyPublisher "SP Video Studio"
#define MyAppExeName "MMO Video Studio.exe"
#define MyAppId "{38CE0934-A2D4-4D9B-9499-AEA7F28FC0EB}"
#define MyUninstallKey "{38CE0934-A2D4-4D9B-9499-AEA7F28FC0EB}_is1"
#define MyAppMutex "Local\MMOVideoStudio.AppInstance.38CE0934A2D44D9B9499AEA7F28FC0EB"

[Setup]
AppId={{38CE0934-A2D4-4D9B-9499-AEA7F28FC0EB}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyPublisher}
AppCopyright=Copyright (c) 2026 SP Video Studio
DefaultDirName={localappdata}\Programs\MMO Video Studio
DefaultGroupName=MMO Video Studio
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
SetupArchitecture=x64
ArchitecturesAllowed=x64os
ArchitecturesInstallIn64BitMode=x64os
MinVersion=10.0.22000
UsePreviousAppDir=yes
UsePreviousGroup=yes
CreateUninstallRegKey=yes
UninstallDisplayIcon={app}\{#MyAppExeName}
UninstallDisplayName={#MyAppName}
SetupIconFile={#MyRepoRoot}\resources\icons\app.ico
OutputDir={#MyOutputDir}
OutputBaseFilename=MMO-Video-Studio-{#MyAppVersion}-Setup
VersionInfoVersion={#MyAppVersionQuad}
VersionInfoProductVersion={#MyAppVersionQuad}
VersionInfoDescription=MMO Video Studio Setup
VersionInfoCompany={#MyPublisher}
VersionInfoCopyright=Copyright (c) 2026 SP Video Studio
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
DisableWelcomePage=no
CloseApplications=yes
RestartApplications=no
AppMutex={#MyAppMutex}
SetupMutex=Local\MMOVideoStudio.Setup.38CE0934A2D44D9B9499AEA7F28FC0EB
RestartIfNeededByRun=no
AlwaysRestart=no
AllowCancelDuringInstall=yes
ChangesAssociations=no
ChangesEnvironment=no

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: unchecked

[Files]
Source: "{#MySourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "{#MyRepoRoot}\packaging\windows\notices\APPLICATION_LICENSE_NOTICE.txt"; DestDir: "{app}\licenses\application"; Flags: ignoreversion

[Icons]
Name: "{group}\MMO Video Studio"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"
Name: "{autodesktop}\MMO Video Studio"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch MMO Video Studio"; Flags: nowait postinstall skipifsilent

[Registry]
; Version marker used only for future installer compatibility/downgrade diagnostics.
Root: HKCU; Subkey: "Software\SP Video Studio\MMO Video Studio"; ValueType: string; ValueName: "InstalledVersion"; ValueData: "{#MyAppVersion}"; Flags: uninsdeletevalue uninsdeletekeyifempty

[Code]
const
  ProductUninstallKey = 'Software\Microsoft\Windows\CurrentVersion\Uninstall\{#MyUninstallKey}';
  ManagedDataRoot = '{localappdata}\MMOVideoStudio';

function NormalizeVersion(const Value: String): String;
var
  I, Dots: Integer;
begin
  Result := Trim(Value);
  Dots := 0;
  for I := 1 to Length(Result) do
    if Result[I] = '.' then
      Dots := Dots + 1;
  while Dots < 3 do
  begin
    Result := Result + '.0';
    Dots := Dots + 1;
  end;
end;

function IsInstalledVersionNewer(): Boolean;
var
  InstalledText, CurrentText: String;
  InstalledVersion, CurrentVersion: Int64;
begin
  Result := False;
  if not RegQueryStringValue(HKCU, ProductUninstallKey, 'DisplayVersion', InstalledText) then
    Exit;

  InstalledText := NormalizeVersion(InstalledText);
  CurrentText := NormalizeVersion('{#MyAppVersion}');
  if not StrToVersion(InstalledText, InstalledVersion) then
  begin
    Log('Could not parse installed DisplayVersion; downgrade guard left unchanged.');
    Exit;
  end;
  if not StrToVersion(CurrentText, CurrentVersion) then
    RaiseException('Installer build version is invalid: ' + CurrentText);

  Result := ComparePackedVersion(InstalledVersion, CurrentVersion) > 0;
  if Result then
    Log(Format('Downgrade blocked: installed=%s installer=%s', [InstalledText, CurrentText]));
end;

function InitializeSetup(): Boolean;
begin
  Result := True;
  if IsInstalledVersionNewer() then
  begin
    if not WizardSilent() then
      MsgBox(
        'A newer version of MMO Video Studio is already installed.' + #13#10 + #13#10 +
        'This installer will not downgrade the application because older versions may not safely open newer project or database schemas.',
        mbError, MB_OK);
    Result := False;
  end;
end;

function HasUninstallSwitch(const SwitchName: String): Boolean;
var
  I: Integer;
begin
  Result := False;
  for I := 1 to ParamCount do
    if CompareText(ParamStr(I), SwitchName) = 0 then
    begin
      Result := True;
      Exit;
    end;
end;

function ConfirmManagedDataRemoval(): Boolean;
var
  DataPath: String;
begin
  DataPath := ExpandConstant(ManagedDataRoot);
  if UninstallSilent() then
  begin
    Result := HasUninstallSwitch('/REMOVEAPPDATA');
    Exit;
  end;

  Result := MsgBox(
    'MMO Video Studio application files have been removed.' + #13#10 + #13#10 +
    'Also remove managed application data from:' + #13#10 +
    DataPath + #13#10 + #13#10 +
    'This includes settings, models, Asset Library data, user templates, cache, recovery, logs, managed downloads/exports, voices, and the local application database.' + #13#10 + #13#10 +
    'Projects or exports stored outside this managed folder are NOT removed.' + #13#10 +
    'Choose No to keep this data for a future reinstall.',
    mbConfirmation, MB_YESNO or MB_DEFBUTTON2) = IDYES;
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  DataPath: String;
begin
  if CurUninstallStep <> usPostUninstall then
    Exit;

  DataPath := ExpandConstant(ManagedDataRoot);
  if DirExists(DataPath) and ConfirmManagedDataRemoval() then
  begin
    Log('Explicit managed application-data removal requested: ' + DataPath);
    if not DelTree(DataPath, True, True, True) then
      MsgBox(
        'Some managed MMO Video Studio application data could not be removed.' + #13#10 + DataPath,
        mbInformation, MB_OK);
  end;
end;
