#!/usr/bin/env python3
"""Generate a simple pamphlet-style PNG from docs/pamphlet.json"""
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).parent.parent
IN = ROOT / 'docs' / 'pamphlet.json'
OUT = ROOT / 'docs' / 'pamphlet.png'

if not IN.exists():
    raise SystemExit('pamphlet.json not found')

with IN.open('r', encoding='utf-8') as f:
    obj = json.load(f)

# Basic page settings
W, H = 1200, 1600
bg = (255, 255, 255)
img = Image.new('RGB', (W, H), bg)
d = ImageDraw.Draw(img)

# Load a default font
try:
    font_h = ImageFont.truetype('arial.ttf', 36)
    font_s = ImageFont.truetype('arial.ttf', 18)
    font_b = ImageFont.truetype('arialbd.ttf', 22)
except Exception:
    font_h = ImageFont.load_default()
    font_s = ImageFont.load_default()
    font_b = ImageFont.load_default()

# Margins
x = 60
y = 50
line_h = 26

# Title
d.text((x, y), obj.get('title', 'Pamphlet'), fill=(10, 30, 80), font=font_h)
y += 60

d.text((x, y), obj.get('overview', ''), fill=(60, 60, 60), font=font_s)
y += 40

for section in obj.get('sections', []):
    heading = section.get('heading')
    if heading:
        d.text((x, y), heading, fill=(0, 80, 140), font=font_b)
        y += 28
    # Body
    body = section.get('body')
    if body:
        # wrap text a bit
        for line in [body[i:i+110] for i in range(0, len(body), 110)]:
            d.text((x+10, y), line, fill=(40, 40, 40), font=font_s)
            y += line_h
        y += 6
    # Items
    for it in section.get('items', []) or []:
        if 'cmd' in it:
            d.text((x+12, y), f"• {it['cmd']}", fill=(0, 0, 0), font=font_s)
            y += line_h
            d.text((x+28, y), it.get('desc', ''), fill=(80, 80, 80), font=font_s)
            y += line_h
        elif 'flag' in it:
            d.text((x+12, y), f"• {it['flag']}", fill=(0, 0, 0), font=font_s)
            y += line_h
            d.text((x+28, y), it.get('desc', ''), fill=(80, 80, 80), font=font_s)
            y += line_h
        elif 'issue' in it:
            d.text((x+12, y), f"• {it['issue']}", fill=(150, 30, 30), font=font_s)
            y += line_h
            d.text((x+28, y), it.get('fix', ''), fill=(80, 80, 80), font=font_s)
            y += line_h
        else:
            d.text((x+12, y), f"• {str(it)}", fill=(0, 0, 0), font=font_s)
            y += line_h
    y += 8

# Footer
d.text((x, H-120), f"Generated: {obj.get('version')}", fill=(120, 120, 120), font=font_s)

OUT.parent.mkdir(parents=True, exist_ok=True)
img.save(OUT)
print(f"Pamphlet image generated: {OUT}")
