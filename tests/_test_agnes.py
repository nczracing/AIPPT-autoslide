# -*- coding: utf-8 -*-
"""Agnes 生图流程实测：走 AutoSlide 的 ImageGenerator 真实代码路径。"""
import os
import sys
from pathlib import Path

# 确保能 import 项目模块
sys.path.insert(0, str(Path(__file__).parent))

from openai import OpenAI
from core.image_generator import ImageGenerator

key = os.environ.get("AGNES_API_KEY", "")
print("AGNES_API_KEY:", ("已找到 " + key[:10] + "...") if key else "缺失")
if not key:
    print("✗ 缺少 AGNES_API_KEY 环境变量")
    sys.exit(1)

# 用环境变量 Key + Agnes base_url 注入 client，走 _generate_ai 真实逻辑
client = OpenAI(
    api_key=key,
    base_url="https://apihub.agnes-ai.com/v1",
    timeout=120.0,
)
ig = ImageGenerator(client=client)

prompt = (
    "A confident young software engineer standing at a crossroads with three glowing "
    "signposts labeled code, team and product, warm studio lighting, flat vector "
    "illustration with subtle gradients and soft shadows, clean balanced composition, high detail"
)
print("正在调用 agnes-image-2.1-flash 生成图片（约 10~30 秒）...")
out_dir = str(Path(__file__).parent / "samples")
path = ig.generate(
    prompt,
    slide_title="职业发展路径",
    output_dir=out_dir,
    filename_prefix="agnes_demo",
    theme="business",
)

if path and os.path.exists(path):
    size_kb = os.path.getsize(path) // 1024
    print(f"✓ Agnes 生图成功: {path} ({size_kb} KB)")
else:
    print(f"✗ Agnes 生图失败，返回: {path}")
    sys.exit(1)
