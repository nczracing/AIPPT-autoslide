## AutoSlide 第27轮 UI 优化审查

### 改动范围
- `ui/theme.py`: 全面视觉主题升级（渐变标题栏、圆角统一、配色优化、移除Qt不支持的CSS属性）
- `ui/main_window.py`: Logo样式优化（字体大小、加粗）
- `ui/generator_widget.py`: 表单标签添加emoji前缀、优化输入框样式
- `ui/preview_widget.py`: 预览卡片样式升级（圆角、阴影、配色）
- `ui/settings_dialog.py`: 配置提示框样式优化

### 审查重点
1. Qt QSS 兼容性：确认无 `transition`、`box-shadow` 等不支持属性
2. 视觉层次：标题栏、输入区、预览区是否有清晰区分
3. 配色一致性：主色 #2f6fed 贯穿整个界面
4. 功能完整性：不影响生成/PPT导出/预览核心功能

### 已做验证
- 编译检查通过（4个UI文件）
- _test_layout.py 12场景通过
- _test_export.py 通过
- PyInstaller 打包成功
- InnoSetup 安装包构建成功
- 冒烟测试通过（exe运行正常，无Qt警告）

### 输出格式
Overall Result: PASS / FAIL (有条件)
Risk Summary: P0/P1/P2/P3
Findings: 每条包含 字段(summary) / risk(P0-P3) / detail / location / status(接受/修复) / reason / alternative
