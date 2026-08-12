; Inno Setup script for NASA Wallpaper 2.0
; Compile after: scripts\build.ps1

[Setup]
AppId={{A7C3E91B-4D2F-4B8A-9E11-NASAWALLPAPER2}}
AppName=NASA Wallpaper
AppVersion=2.1.1
AppPublisher=PC BAAZ
AppPublisherURL=https://github.com/pcbaaz/NASA-Wallpaper
DefaultDirName={autopf}\PC BAAZ\NASA Wallpaper
DefaultGroupName=PC BAAZ\NASA Wallpaper
UninstallDisplayIcon={app}\NASA_Wallpaper.exe
Compression=lzma2
SolidCompression=yes
OutputDir=installer
OutputBaseFilename=NASA_Wallpaper_Setup
SetupIconFile=assets\icon.ico
PrivilegesRequired=lowest
ArchitecturesInstallIn64BitMode=x64compatible
WizardStyle=modern
MinVersion=10.0

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop icon"; GroupDescription: "Additional icons:"
Name: "startup"; Description: "Run on Windows startup"; GroupDescription: "Startup options:"; Flags: unchecked

[Files]
Source: "dist\NASA_Wallpaper\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\NASA Wallpaper"; Filename: "{app}\NASA_Wallpaper.exe"
Name: "{group}\Uninstall NASA Wallpaper"; Filename: "{uninstallexe}"
Name: "{autodesktop}\NASA Wallpaper"; Filename: "{app}\NASA_Wallpaper.exe"; Tasks: desktopicon

[Registry]
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "NASAWallpaper"; ValueData: """{app}\NASA_Wallpaper.exe"""; Flags: uninsdeletevalue; Tasks: startup

[Run]
Filename: "{app}\NASA_Wallpaper.exe"; Description: "Launch NASA Wallpaper"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}"
