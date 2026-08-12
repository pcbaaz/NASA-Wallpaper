; Inno Setup — NASA Wallpaper
; Built by GitHub Actions / scripts\build.ps1

#define MyAppName "NASA Wallpaper"
#define MyAppVersion "2.4.0"
#define MyAppPublisher "PC BAAZ"
#define MyAppURL "https://github.com/pcbaaz/NASA-Wallpaper"
#define MyAppExeName "NASA_Wallpaper.exe"

[Setup]
AppId={{A7C3E91B-4D2F-4B8A-9E11-NASAWALLPAPER2}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}/releases/latest
DefaultDirName={localappdata}\Programs\PC BAAZ\NASA Wallpaper
DefaultGroupName=PC BAAZ\NASA Wallpaper
UninstallDisplayIcon={app}\{#MyAppExeName}
Compression=lzma2
SolidCompression=yes
OutputDir=installer
OutputBaseFilename=NASA_Wallpaper_Setup
SetupIconFile=assets\icon.ico
PrivilegesRequired=lowest
ArchitecturesInstallIn64BitMode=x64compatible
WizardStyle=modern
MinVersion=10.0
DisableProgramGroupPage=yes
AllowNoIcons=no

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
; Desktop shortcut + Run at startup ON by default
Name: "desktopicon"; Description: "Create a desktop icon"; GroupDescription: "Additional icons:"; Flags: checkedonce
Name: "startup"; Description: "Run when Windows starts"; GroupDescription: "Startup options:"; Flags: checkedonce

[Files]
Source: "dist\NASA_Wallpaper.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "assets\icon.ico"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\icon.ico"
Name: "{group}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\icon.ico"; Tasks: desktopicon

[Registry]
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "NASAWallpaper"; ValueData: """{app}\{#MyAppExeName}"""; Flags: uninsdeletevalue; Tasks: startup

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch NASA Wallpaper now"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}"
