; AutoSlide 安装脚本 (Inno Setup 6)
; 生成单文件安装包 AutoSlide-Setup.exe
; 注意：本脚本全部使用 __DIR__ 相对路径（脚本所在目录 scripts/ 的上级为项目根），
;       项目迁移/改名不再需要改动本文件。请在 scripts/ 目录或其任意位置运行：
;       "C:/Users/NCZ Racing/InnoSetup6/ISCC.exe" E:/.../autoslide/scripts/autoslide_setup.iss
;       （Inno Setup 自动按脚本自身位置解析 __DIR__，与工作目录无关）

#define MyAppName "AutoSlide"
#define MyAppVersion "1.1"
#define MyAppPublisher "NCZ Racing"
#define MyAppExeName "AutoSlide.exe"
; 项目根目录 = 本脚本所在目录(scripts/)的上一级
#define ProjectRoot __DIR__ + "..\"

[Setup]
AppId={{B7C3E5A1-9D4F-4E2B-8A6C-1F3E7D9B2C4A}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
; 用户级安装（免 UAC）：安装到 %LOCALAPPDATA%\Programs\AutoSlide，避免与 lowest 权限冲突
DefaultDirName={localappdata}\Programs\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir={#ProjectRoot}installer
OutputBaseFilename=AutoSlide-Setup
SetupIconFile={#ProjectRoot}resources\icons\app.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
UninstallDisplayName={#MyAppName}
VersionInfoCopyright=Copyright (c) 2026 NCZ Racing
LicenseFile={#ProjectRoot}LICENSE
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
; 路径用 __DIR__ 相对定位，项目迁移无需改动本行。
Source: "{#ProjectRoot}dist\{#MyAppName}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#MyAppName}}"; Flags: nowait postinstall skipifsilent
