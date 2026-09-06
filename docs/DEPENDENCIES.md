# AutoSlide 项目依赖配置

## Python 依赖 (requirements.txt)

```
PyQt6>=6.5.0
python-pptx>=0.6.23
openai>=1.0.0
requests>=2.31.0
pillow>=10.0.0
pyinstaller>=6.0.0
```

## 系统要求

- Windows 10/11
- Python 3.10+
- 网络连接（用于AI API调用）

## 开发环境

```bash
# 创建虚拟环境
python -m venv venv
venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 运行开发版本
python main.py

# 打包发布
pyinstaller --noconfirm autoslide.spec
```
