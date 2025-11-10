from PIL import Image
import json, sys, os

if len(sys.argv) < 2:
    print('Usage: python gauge_crops.py <collision_report.json>')
    sys.exit(1)

report_path = sys.argv[1]
with open(report_path, 'r') as f:
    r = json.load(f)
img = Image.open(r['image'])
img_w, img_h = img.size
out_dir = os.path.splitext(report_path)[0] + '_gauge_crops'
os.makedirs(out_dir, exist_ok=True)
for item in r['items']:
    if item['type'] == 'gauge':
        left, top, right, bottom = item['rect']
        pad = int(max(20, 0.05 * max(right-left, bottom-top)))
        l = max(0, left - pad)
        t = max(0, top - pad)
        rgt = min(img_w, right + pad)
        b = min(img_h, bottom + pad)
        crop = img.crop((l,t,rgt,b))
        out_path = os.path.join(out_dir, f"{item['name']}_crop.png")
        crop.save(out_path)
        print('Wrote', out_path)
print('Done')
