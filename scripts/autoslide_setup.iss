; AutoSlide 安装脚本 (Inno Setup 6)
; 生成单文件安装包 AutoSlide-Setup.exe
; 注意：请在项目根目录运行 `ISCC.exe autoslide_setup.iss`（相对路径 Source/OutputDir 依赖此前提）

#define MyAppName "AutoSlide"
#define MyAppVersion "1.1"
#define MyAppPublisher "NCZ Racing"
#define MyAppExeName "AutoSlide.exe"

[Setup]
AppId={{B7C3E5A1-9D4F-4E2B-8A6C-1F3E7D9B2C4A}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
; 用户级安装（免 UAC）：安装到 %LOCALAPPDATA%\Programs\AutoSlide，避免与 lowest 权限冲突
DefaultDirName={localappdata}\Programs\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir=E:\life\study\projects\autos\autoslide\installer
OutputBaseFilename=AutoSlide-Setup
SetupIconFile=E:\life\study\projects\autos\autoslide\resources\icons\app.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
UninstallDisplayName={#MyAppName}
VersionInfoCopyright=Copyright (c) 2026 NCZ Racing
LicenseFile=E:\life\study\projects\autos\autoslide\LICENSE
Compression=lzma2/max
SolidCompression=yes
PrivilegesRequired=lowest
WizardStyle=modern
CloseApplications=yes
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "chinesesimp"; MessagesFile: "compiler:Languages\ChineseSimplified.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; 关键修复：onedir 模式必须递归打包整个 dist\AutoSlide\ 目录（含 _internal 依赖）。
; 旧版只复制单个 exe（onefile 时代的写法），会导致安装后缺少依赖而无法启动。
Source: "E:\life\study\projects\autos\autoslide\dist\{#MyAppName}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#MyAppName}}"; Flags: nowait postinstall skipifsilent
