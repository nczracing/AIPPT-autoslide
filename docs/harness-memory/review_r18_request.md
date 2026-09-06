# 第 18 轮审查 · Review Package：单文件安装包（Inno Setup）

## 一、原始需求
用户要求：把 AutoSlide 打包成一个「单文件安装包」（即双击即可安装的 setup.exe，而非绿色版单文件 exe）。

## 二、实现摘要

### 交付物
| 文件 | 说明 |
|------|------|
| `installer/AutoSlide-Setup.exe` | 单文件安装程序（60.9 MB），LZMA2 最大压缩 |
| `autoslide_setup.iss` | Inno Setup 6.7.3 构建脚本（可复现） |
| `resources/icons/app.ico` | PIL 绘制的应用图标（16~256 多尺寸） |

### 工具链
- Inno Setup 6.7.3 安装到用户目录 `C:\Users\NCZ Racing\InnoSetup6\`（无需管理员）
- 中文语言文件 `ChineseSimplified.isl`（issrc 仓库 Unofficial 目录，已规范化为 UTF-8 BOM + CodePage 65001）
- 图标用 Python PIL 生成（蓝紫渐变圆角方形 + 白色幻灯片轮廓 + 播放三角形）

### 安装脚本关键配置（autoslide_setup.iss）
- `PrivilegesRequired=lowest`：允许非管理员安装
- `DefaultDirName={autopf}\AutoSlide`：优先 Program Files，无权限回退用户目录
- `ArchitecturesAllowed/InstallIn64BitMode=x64compatible`
- 双语言：`chinesesimp`（ChineseSimplified.isl）+ `english`（Default.isl）
- `[Tasks]` desktopicon 默认不勾选
- `[Icons]` 开始菜单 + 桌面（可选）+ 卸载快捷方式
- `[Run]` 安装完成后可选启动（nowait postinstall skipifsilent）
- `CloseApplications=yes`：安装前关闭运行中的程序

## 三、修改/新增文件
1. `autoslide_setup.iss`（新增，Inno Setup 脚本）
2. `resources/icons/app.ico`（新增，PIL 生成）
3. `installer/AutoSlide-Setup.exe`（构建产物）

## 四、验证结果
- ISCC 编译成功（6.4s），无警告
- 安装包 SHA256 校验通过（与官方 Inno Setup 安装包一致）
- 静默安装：正确解压出 AutoSlide.exe + unins000.exe + unins000.dat
- 安装后冒烟测试：进程存活、日志进入事件循环、无报错
- 卸载测试：unins000.exe 退出码 0，正确清理文件

## 五、环境背景（供审查参考）
本机 DNS（114.114.114.114）失效、GitHub 直连被墙，通过「223.5.5.5 解析 + curl --resolve」绕过 DNS、「ghfast.top」代理下载 GitHub 资源。工具链已就位，`ISCC.exe autoslide_setup.iss` 可复现构建。
