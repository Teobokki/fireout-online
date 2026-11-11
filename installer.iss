#define MyVer "1.0.0"
[Setup]
AppId={{EB2E0F1F-3094-46A7-A749-4D754A5D3244}
AppName=FIREOUT ONLINE
AppVersion={#MyVer}
AppVerName=FIREOUT ONLINE {#MyVer}
AppPublisher=EX Inc.
AppPublisherURL=https://github.com/Teobokki/fireout-online
AppCopyright=©2026 EX ROMANIA/EX INC.
VersionInfoVersion={#MyVer}
VersionInfoCompany=EX Inc.
VersionInfoCopyright=©2026 EX ROMANIA/EX INC.
VersionInfoProductName=FIREOUT ONLINE
VersionInfoDescription=FIREOUT ONLINE Setup
DefaultDirName={localappdata}\Programs\FIREOUT ONLINE
DefaultGroupName=FIREOUT ONLINE
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=dist
OutputBaseFilename=FIREOUT-ONLINE-Setup-{#MyVer}
SetupIconFile=assets\icon.ico
UninstallDisplayIcon={app}\FIREOUT ONLINE.exe
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
CloseApplications=force

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[InstallDelete]
Type: filesandordirs; Name: "{app}\_internal"

[Files]
Source: "dist\FIREOUT ONLINE\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\FIREOUT ONLINE"; Filename: "{app}\FIREOUT ONLINE.exe"
Name: "{group}\Uninstall FIREOUT ONLINE"; Filename: "{uninstallexe}"
Name: "{userdesktop}\FIREOUT ONLINE"; Filename: "{app}\FIREOUT ONLINE.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\FIREOUT ONLINE.exe"; Description: "Launch FIREOUT ONLINE now"; Flags: nowait postinstall skipifsilent
