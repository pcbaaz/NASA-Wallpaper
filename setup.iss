[Setup]
AppName=NASA Wallpaper
AppVersion=7.3
AppPublisher=PC BAAZ
AppPublisherURL=https://www.youtube.com/@PC-BAAZ
DefaultDirName={pf}\PC BAAZ\NASA Wallpaper
DefaultGroupName=PC BAAZ\NASA Wallpaper
UninstallDisplayIcon={app}\NASA_Wallpaper.exe
Compression=lzma2
SolidCompression=yes
OutputDir=installer
OutputBaseFilename=NASA_Wallpaper_Setup
SetupIconFile=icon.ico

; ========== FIX: Request admin privileges ==========
PrivilegesRequired=admin

AllowNoIcons=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop icon"; GroupDescription: "Additional icons:"
Name: "startup"; Description: "Run on Windows startup"; GroupDescription: "Startup options:"

[Files]
Source: "dist\NASA_Wallpaper\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\NASA Wallpaper"; Filename: "{app}\NASA_Wallpaper.exe"
Name: "{group}\Uninstall NASA Wallpaper"; Filename: "{uninstallexe}"
Name: "{commondesktop}\NASA Wallpaper"; Filename: "{app}\NASA_Wallpaper.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\NASA_Wallpaper.exe"; Description: "Run NASA Wallpaper now"; Flags: postinstall nowait

[Registry]
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "NASAWallpaper"; ValueData: """{app}\NASA_Wallpaper.exe"""; Flags: uninsdeletevalue; Tasks: startup

[UninstallDelete]
Type: filesandordirs; Name: "{app}"