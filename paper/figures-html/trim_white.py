#!/usr/bin/env python3
"""trim_white.py — 自动裁掉 PNG 四周白边，保留 pad 像素余量（印刷安全距）。"""
import sys
from PIL import Image

PAD = 24  # 3x 缩放下 24px ≈ 8css px

for path in sys.argv[1:]:
    im = Image.open(path).convert('RGB')
    w, h = im.size
    # 找非纯白内容的边界（容忍接近白的抗锯齿像素）
    gray = im.convert('L')
    # 二值化：非白(<250)为内容
    bbox_img = gray.point(lambda x: 0 if x > 248 else 255)
    bbox = bbox_img.getbbox()
    if not bbox:
        print('skip (blank):', path)
        continue
    l, t, r, b = bbox
    l = max(0, l - PAD); t = max(0, t - PAD)
    r = min(w, r + PAD); b = min(h, b + PAD)
    im.crop((l, t, r, b)).save(path)
    print(f'trimmed {path}: {w}x{h} -> {r-l}x{b-t}')
