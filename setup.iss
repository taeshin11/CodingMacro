[Setup]
AppName=CodingMacro
AppVersion=1.0
AppPublisher=CodingMacro
DefaultDirName={autopf}\CodingMacro
DefaultGroupName=CodingMacro
UninstallDisplayIcon={app}\CodingMacro.exe
OutputDir=installer
OutputBaseFilename=CodingMacro_Setup_v3
Compression=lzma2
SolidCompression=yes
PrivilegesRequired=admin
ArchitecturesInstallIn64BitMode=x64compatible

[Files]
Source: "dist\CodingMacro.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\CodingMacro"; Filename: "{app}\CodingMacro.exe"
Name: "{group}\Uninstall CodingMacro"; Filename: "{uninstallexe}"
Name: "{commondesktop}\CodingMacro"; Filename: "{app}\CodingMacro.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"

[Run]
Filename: "{app}\CodingMacro.exe"; Description: "Launch CodingMacro"; Flags: nowait postinstall skipifsilent
