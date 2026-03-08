; Inno Setup script for Windows installer (.exe)
[Setup]
AppId={{CBEFFFC5-6A33-450D-AC95-4A2F2E6F4A47}
AppName=Hyper Search for Windows 11
AppVersion=1.0.0
AppPublisher=Ninad
DefaultDirName={localappdata}\Programs\HyperSearch
DefaultGroupName=Hyper Search
UninstallDisplayIcon={app}\HyperSearch.exe
OutputDir=dist_installer
OutputBaseFilename=HyperSearchInstaller
Compression=lzma
SolidCompression=yes
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=lowest
WizardStyle=modern
MinVersion=10.0

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Files]
Source: "dist\HyperSearch.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\Hyper Search"; Filename: "{app}\HyperSearch.exe"
Name: "{autodesktop}\Hyper Search"; Filename: "{app}\HyperSearch.exe"

[Run]
Filename: "{app}\HyperSearch.exe"; Description: "Launch Hyper Search"; Flags: nowait postinstall skipifsilent
