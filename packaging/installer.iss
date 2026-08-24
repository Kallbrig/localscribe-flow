#define MyAppName "LocalScribe"
#define MyAppVersion "0.1.9"
#define MyAppPublisher "LocalScribe contributors"
#define MyAppExeName "LocalScribe.exe"

[Setup]
AppId={{BF1E295C-97D2-4C86-8EC8-AFAE7C84DAA7}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\LocalScribe
DefaultGroupName={#MyAppName}
OutputDir=..\release
OutputBaseFilename=LocalScribe-{#MyAppVersion}-Setup
Compression=lzma2
SolidCompression=yes
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=lowest
WizardStyle=modern

[Files]
Source: "..\dist\LocalScribe\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[InstallDelete]
Type: files; Name: "{app}\LocalScribe Flow.exe"
Type: files; Name: "{autoprograms}\LocalScribe Flow.lnk"
Type: files; Name: "{autodesktop}\LocalScribe Flow.lnk"

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional icons:"

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch {#MyAppName}"; Flags: nowait postinstall skipifsilent
