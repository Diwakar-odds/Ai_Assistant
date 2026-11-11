; Pulsar AI Assistant - Production Inno Setup 6 Script
; Optional industry-standard installer alternative to Setup_Pulsar.exe.
; Requires Inno Setup 6 (iscc.exe) after building dist_package\Pulsar_AI_Assistant via desktop\build_exe.bat.

#define MyAppName "Pulsar AI Assistant"
#define MyAppVersion "4.0.0"
#define MyAppPublisher "Pulsar AI Project"
#define MyAppExeName "Pulsar_AI_Assistant.exe"

[Setup]
AppId={{8D6B4F91-62B3-4F2A-9D5E-19A72F8C4E01}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={localappdata}\Programs\PulsarAI
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=auto
PrivilegesRequired=lowest
LicenseFile=..\..\docs\LICENSE.txt
SetupIconFile=..\..\assets\icon.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
OutputDir=..\..\dist_package
OutputBaseFilename=Pulsar_AI_Setup_v{#MyAppVersion}
Compression=lzma2/normal
SolidCompression=yes
WizardStyle=modern

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Types]
Name: "full"; Description: "Full Installation (Recommended)"
Name: "compact"; Description: "Core Application Only"
Name: "custom"; Description: "Custom Installation"; Flags: iscustom

[Components]
Name: "core"; Description: "Pulsar AI Core Engine & Desktop App"; Types: full compact custom; Flags: fixed
Name: "overlay"; Description: "Floating 4D Orb Desktop Overlay & Wake-Word Service"; Types: full custom

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"
Name: "autostart"; Description: "Launch Pulsar AI automatically when Windows starts"; GroupDescription: "System Integration:"

[Files]
Source: "..\..\dist_package\Pulsar_AI_Assistant\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs; Components: core
Source: "..\..\docs\LICENSE.txt"; DestDir: "{app}"; Flags: ignoreversion; Components: core

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Registry]
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "PulsarAIAssistant"; ValueData: """{app}\{#MyAppExeName}"""; Flags: uninsdeletevalue; Tasks: autostart

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[Code]
function IsWebView2Installed(): Boolean;
var
  Version: String;
begin
  Result :=
    (RegQueryStringValue(HKLM, 'SOFTWARE\WOW6432Node\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}', 'pv', Version) and (Version <> '') and (Version <> '0.0.0.0')) or
    (RegQueryStringValue(HKLM, 'SOFTWARE\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}', 'pv', Version) and (Version <> '') and (Version <> '0.0.0.0')) or
    (RegQueryStringValue(HKCU, 'Software\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}', 'pv', Version) and (Version <> '') and (Version <> '0.0.0.0'));
end;

function InitializeSetup(): Boolean;
var
  ErrCode: Integer;
begin
  Result := True;
  if not IsWebView2Installed() then
  begin
    if MsgBox('Microsoft Edge WebView2 Runtime is required for the Pulsar desktop interface.' + #13#10 +
              'Would you like to open Microsoft''s download page before continuing?',
              mbConfirmation, MB_YESNO) = IDYES then
    begin
      ShellExec('open', 'https://go.microsoft.com/fwlink/p/?LinkId=2124703', '', '', SW_SHOW, ewNoWait, ErrCode);
    end;
  end;
end;
