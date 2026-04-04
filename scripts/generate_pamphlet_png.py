#!/usr/bin/env python3
"""Generate a simple pamphlet-style PNG from docs/pamphlet.json"""

import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).parent.parent
IN = ROOT / "docs" / "pamphlet.json"
OUT = ROOT / "docs" / "pamphlet.png"

if not IN.exists():
    raise SystemExit("pamphlet.json not found")

with IN.open("r", encoding="utf-8") as f:
    obj = json.load(f)

# Basic assets: background and fonts
bg = (255, 255, 255)
try:
    font_h = ImageFont.truetype("arial.ttf", 36)
    font_s = ImageFont.truetype("arial.ttf", 18)
    font_b = ImageFont.truetype("arialbd.ttf", 22)
except Exception:
    # Fallback to default fonts if system fonts unavailable
    font_h = ImageFont.load_default()
    font_s = ImageFont.load_default()
    font_b = ImageFont.load_default()

# Build lines to draw and measure required height
import textwrap

lines = []  # tuples of (text, font, fill)

# Title
lines.append((obj.get("title", "Pamphlet"), font_h, (10, 30, 80)))
lines.append((obj.get("overview", ""), font_s, (60, 60, 60)))
lines.append(("", font_s, (0, 0, 0)))

for section in obj.get("sections", []):
    heading = section.get("heading")
    if heading:
        lines.append((heading, font_b, (0, 80, 140)))
    body = section.get("body")
    if body:
        wrapped = textwrap.wrap(body, width=100)
        for wline in wrapped:
            lines.append((wline, font_s, (40, 40, 40)))
    items = section.get("items", []) or []
    for it in items:
        if "cmd" in it:
            lines.append((f"• {it['cmd']}", font_s, (0, 0, 0)))
            for desc_line in textwrap.wrap(it.get("desc", ""), width=90):
                lines.append((f"  {desc_line}", font_s, (80, 80, 80)))
        elif "flag" in it:
            lines.append((f"• {it['flag']}", font_s, (0, 0, 0)))
            for desc_line in textwrap.wrap(it.get("desc", ""), width=90):
                lines.append((f"  {desc_line}", font_s, (80, 80, 80)))
        elif "issue" in it:
            lines.append((f"• {it['issue']}", font_s, (150, 30, 30)))
            for fix_line in textwrap.wrap(it.get("fix", ""), width=90):
                lines.append((f"  {fix_line}", font_s, (80, 80, 80)))
        elif "cmd" not in it and "flag" not in it and "issue" not in it:
            # generic item
            lines.append((f"• {it!s}", font_s, (0, 0, 0)))

# Footer
footer = f"Generated: {obj.get('version')}"

# Estimate image height
x = 60
margin_top = 50
margin_bottom = 80
spacing = 6
curr_y = margin_top
# We need a temporary ImageDraw to measure text sizes
_tmp_img = Image.new("RGB", (1200, 100), bg)
_tmp_draw = ImageDraw.Draw(_tmp_img)
required_height = curr_y
for text, fnt, _ in lines:
    bbox = _tmp_draw.textbbox((0, 0), text, font=fnt)
    line_h = bbox[3] - bbox[1]
    required_height += line_h + spacing
required_height += margin_bottom + 40  # room for footer

# Create final image with computed height
W = 1200
H = max(900, required_height)
img = Image.new("RGB", (W, H), bg)
d = ImageDraw.Draw(img)

# Draw the lines
y = margin_top
for text, fnt, fill in lines:
    d.text((x, y), text, fill=fill, font=fnt)
    bbox = d.textbbox((x, y), text, font=fnt)
    line_h = bbox[3] - bbox[1]
    y += line_h + spacing

# Footer
d.text((x, H - margin_bottom), footer, fill=(120, 120, 120), font=font_s)

OUT.parent.mkdir(parents=True, exist_ok=True)
img.save(OUT)
print(f"Pamphlet image generated: {OUT} (size: {W}x{H})")
