; Inno Setup script for the Windows installer.
; Build with `make package-windows ARGS="--installer"` (build.py passes AppVersion).
; The .iss file must stay UTF-8 *with BOM* for Inno Setup to read the Chinese.

#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif

; Inno Setup does not ship a Simplified Chinese translation. When the user has
; dropped ChineseSimplified.isl into their Languages folder, use it; otherwise
; the wizard falls back to English while our own strings stay Chinese.
#define ChineseMessages ""
#if FileExists(AddBackslash(CompilerPath) + "Languages\ChineseSimplified.isl")
  #undef ChineseMessages
  #define ChineseMessages "compiler:Languages\ChineseSimplified.isl"
#endif

[Setup]
AppId={{8054E44B-DDA8-49DD-B4C0-6CCEC3ACBD55}
AppName=Kotobako
AppVersion={#AppVersion}
AppPublisher=Kotobako
DefaultDirName={localappdata}\Programs\Kotobako
DefaultGroupName=Kotobako
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=..\dist
OutputBaseFilename=Kotobako-{#AppVersion}-setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\Kotobako.exe
SetupLogging=yes

[Languages]
#if ChineseMessages != ""
Name: "chinesesimplified"; MessagesFile: {#ChineseMessages}
#endif
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "创建桌面快捷方式"; GroupDescription: "附加任务："; Flags: unchecked

[Files]
Source: "..\dist\Kotobako\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion

[Icons]
Name: "{autoprograms}\Kotobako"; Filename: "{app}\Kotobako.exe"; Parameters: "--open"; Comment: "日语学习伴侣"
Name: "{autodesktop}\Kotobako"; Filename: "{app}\Kotobako.exe"; Parameters: "--open"; Comment: "日语学习伴侣"; Tasks: desktopicon

[Run]
Filename: "{app}\Kotobako.exe"; Parameters: "--open"; Description: "启动 ことばこ"; Flags: nowait postinstall skipifsilent
