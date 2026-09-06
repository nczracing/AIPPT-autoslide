# -*- coding: utf-8 -*-
"""验证动画 XML 是否合法（符合 PowerPoint schema）"""
import sys, os, zipfile, re
sys.path.insert(0, '.')
from PIL import Image as PILImage
from lxml import etree
from settings_module import Presentation, Slide
from core.pptx_builder import PPTXBuilder

P = '{http://schemas.openxmlformats.org/presentationml/2006/main}'
img = PILImage.new("RGB", (1200, 600), (100, 150, 200))
img.save('_anim_test.png')

p = Presentation(title="动画验证", theme="business", language="zh")
p.add_slide(Slide(page=1, title="标题页动画", points=["要点一", "要点二", "要点三"],
                  detail="这是详细正文内容，用于验证动画。", layout="title_content",
                  image_path="_anim_test.png", image_layout="right"))
p.add_slide(Slide(page=2, title="双栏动画", points=["左栏要点", "右栏要点"], detail="说明文字",
                  layout="two_content"))
p.add_slide(Slide(page=3, title="无图页", points=["甲", "乙"], detail="纯文字页", layout="title_content"))

out = "_anim_verify.pptx"
PPTXBuilder().build(p, out)
print(f"生成: {out}\n")

z = zipfile.ZipFile(out)
ok = True
for n in sorted(z.namelist()):
    if not re.match(r'ppt/slides/slide\d+\.xml$', n):
        continue
    x = z.read(n).decode('utf-8')
    root = etree.fromstring(z.read(n))
    kids = [etree.QName(c).localname for c in root]
    print(f"--- {n} ---")
    print(f"  sld 子元素顺序: {kids}")

    # 1. 非法元素必须清零
    for bad in ('sldTrans', 'animCue', 'animSeq', 'fadeTg', 'moveTg'):
        found = [e.tag for e in root.iter() if etree.QName(e).localname == bad]
        if found:
            print(f"  ✗ 仍存在非法元素 {bad}")
            ok = False
    print("  非法元素(sldTrans/animCue/animSeq): 清零 ✓")

    # 2. transition 必须是 sld 直接子元素且在 timing 之前
    if 'transition' in kids:
        ti, tr = kids.index('transition'), (kids.index('timing') if 'timing' in kids else 999)
        status = '✓ 顺序正确' if tr == 999 or ti < tr else '✗ 位置错误'
        print(f"  transition 直接子元素 ✓，位置 {ti} {'早于' if tr!=999 else '（无timing）'}timing → {status}")
        if tr != 999 and ti > tr:
            ok = False
    else:
        print("  transition: 无（封面/文献页豁免）")

    # 3. timing 树结构
    if 'timing' in kids:
        t = root.find(f'{P}timing')
        effects = [e.get('filter') for e in t.iter() if etree.QName(e).localname == 'animEffect']
        spids = [e.get('spid') for e in t.iter() if etree.QName(e).localname == 'spTgt']
        nodes = [e.get('nodeType') for e in t.iter() if etree.QName(e).localname == 'cTn' and e.get('nodeType')]
        seqs = [e.get('nodeType') for e in t.iter() if etree.QName(e).localname == 'cTn'
                and e.get('nodeType') in ('mainSeq','tmRoot')]
        print(f"  timing ✓ 动画数={len(effects)} 效果={effects}")
        print(f"    目标spid={spids}")
        print(f"    节点类型={nodes}")
        print(f"    主序列={seqs}")
        if 'mainSeq' not in seqs or 'tmRoot' not in seqs:
            print("  ✗ 缺少 mainSeq/tmRoot 根节点")
            ok = False
        if not effects:
            print("  ✗ 无 animEffect 动画")
            ok = False
    else:
        print("  timing: 无 ✗（应有动画）")
        ok = False
    print()

print("=" * 50)
print("✓ 动画 XML 全部合法" if ok else "✗ 存在问题")
