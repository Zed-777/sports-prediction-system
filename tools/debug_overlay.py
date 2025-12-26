import os
import sys

from PIL import Image, ImageDraw, ImageFont


# Maps data coordinates (x in [0,10], y in [0,20]) to pixel coords for the PNG
def data_to_pixels(x, y, w, h, img_w, img_h):
    left = int((x / 10.0) * img_w)
    # In data coords y increases upward; image has origin at top-left
    top = int(((20.0 - (y + h)) / 20.0) * img_h)
    width = int((w / 10.0) * img_w)
    height = int((h / 20.0) * img_h)
    return (left, top, left + width, top + height)


def draw_overlay(image_path, out_path=None):
    img = Image.open(image_path).convert("RGBA")
    img_w, img_h = img.size
    overlay = Image.new("RGBA", img.size, (255, 255, 255, 0))
    draw = ImageDraw.Draw(overlay)

    # Try to load a default font
    try:
        font = ImageFont.truetype("arial.ttf", 24)
    except Exception:
        font = ImageFont.load_default()

    # Define sections (x,y,width,height) in data coordinates (same as in generate_fast_reports.py)
    regions = [
        ("main_box", (0.2, 0.3, 9.6, 19.4), (30, 144, 255, 80)),
        ("header_bg", (0.4, 17.5, 9.2, 2.2), (0, 0, 0, 120)),
        ("inner_border", (0.3, 0.4, 9.4, 19.2), (120, 120, 120, 60)),
        ("results_bg", (0.6, 14.5, 8.8, 2.8), (200, 100, 200, 120)),
        ("win_bg", (0.5, 11.3, 9.0, 2.8), (100, 200, 220, 120)),
        ("perf_bg", (0.6, 9.0, 8.8, 2.2), (52, 152, 219, 100)),
        ("goals_bg", (0.6, 6.5, 8.8, 2.2), (243, 156, 18, 100)),
        ("factors_bg", (0.6, 4.0, 8.8, 2.2), (155, 89, 182, 100)),
    ]

    for name, (x, y, w, h), color in regions:
        rect = data_to_pixels(x, y, w, h, img_w, img_h)
        draw.rectangle(rect, outline=color, fill=color)
        # label
        draw.text(
            (rect[0] + 6, rect[1] + 6),
            f"{name} {x:.2f},{y:.2f}",
            font=font,
            fill=(0, 0, 0, 220),
        )

    # Define gauges (center_x, center_y, radius) -> convert to bbox
    gauges = [
        ("confidence", (2.0, 11.7, 0.45), (46, 204, 113, 180)),
        ("data_quality", (8.0, 11.7, 0.45), (46, 204, 113, 180)),
        ("home_form", (2.5, 10.0, 0.45), (46, 134, 193, 180)),
        ("away_form", (7.5, 10.0, 0.45), (46, 134, 193, 180)),
        ("over_2.5", (2.8, 7.6, 0.4), (241, 196, 15, 180)),
        ("btts", (7.2, 7.6, 0.4), (241, 196, 15, 180)),
    ]

    for name, (cx, cy, r), color in gauges:
        x = cx - r
        y = cy - r
        w = 2 * r
        h = 2 * r
        rect = data_to_pixels(x, y, w, h, img_w, img_h)
        draw.ellipse(rect, outline=color, fill=(color[0], color[1], color[2], 120))
        draw.text(
            (rect[0] + 4, rect[1] + 4),
            f"{name} c=({cx:.2f},{cy:.2f}) r={r:.2f}",
            font=font,
            fill=(0, 0, 0, 220),
        )

    # Column labels (win/draw/away) approximate boxes
    cols = [
        (2.2, 13.2, 1.0, 0.8, "home_col"),
        (5.0, 13.2, 1.0, 0.8, "draw_col"),
        (7.8, 13.2, 1.0, 0.8, "away_col"),
    ]
    for x, y, w, h, name in cols:
        rect = data_to_pixels(x - w / 2, y - h / 2, w, h, img_w, img_h)
        draw.rectangle(rect, outline=(0, 0, 0, 180), fill=(255, 255, 255, 120))
        draw.text((rect[0] + 4, rect[1] + 4), name, font=font, fill=(0, 0, 0, 220))

    # Save overlayed image
    combined = Image.alpha_composite(img, overlay)
    out_path = out_path or os.path.splitext(image_path)[0] + "_debug_overlay.png"
    combined.convert("RGB").save(out_path, dpi=(300, 300))
    print(f"Wrote overlay file: {out_path}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python debug_overlay.py <path_to_prediction_card.png> [out_path]")
        sys.exit(1)
    image_path = sys.argv[1]
    out_path = sys.argv[2] if len(sys.argv) > 2 else None
    draw_overlay(image_path, out_path)
