import json
import os
import sys

from PIL import Image


# identical mapping used by debug_overlay
def data_to_pixels_rect(x, y, w, h, img_w, img_h):
    left = int((x / 10.0) * img_w)
    top = int(((20.0 - (y + h)) / 20.0) * img_h)
    width = int((w / 10.0) * img_w)
    height = int((h / 20.0) * img_h)
    return (left, top, left + width, top + height)


def area(rect):
    left, top, right, bottom = rect
    w = max(0, right - left)
    h = max(0, bottom - top)
    return w * h


def intersect(a, b):
    left = max(a[0], b[0])
    top = max(a[1], b[1])
    right = min(a[2], b[2])
    bottom = min(a[3], b[3])
    if right <= left or bottom <= top:
        return None
    return (left, top, right, bottom)


def main(image_path):
    img = Image.open(image_path)
    img_w, img_h = img.size

    regions = [
        ('main_box', (0.2, 0.3, 9.6, 19.4)),
        ('header_bg', (0.4, 17.5, 9.2, 2.2)),
        ('inner_border', (0.3, 0.4, 9.4, 19.2)),
        ('results_bg', (0.6, 14.5, 8.8, 2.8)),
        ('win_bg', (0.5, 11.3, 9.0, 2.8)),
        ('perf_bg', (0.6, 9.0, 8.8, 2.2)),
        ('goals_bg', (0.6, 6.5, 8.8, 2.2)),
        ('factors_bg', (0.6, 4.0, 8.8, 2.2)),
    ]

    gauges = [
        ('confidence', (2.0, 11.7, 0.45)),
        ('data_quality', (8.0, 11.7, 0.45)),
        ('home_form', (2.5, 10.0, 0.45)),
        ('away_form', (7.5, 10.0, 0.45)),
        ('over_2.5', (2.8, 7.6, 0.4)),
        ('btts', (7.2, 7.6, 0.4)),
    ]

    cols = [ ('home_col', (2.2 - 0.5, 13.2 - 0.4, 1.0, 0.8)), ('draw_col', (5.0 - 0.5, 13.2 - 0.4, 1.0, 0.8)), ('away_col', (7.8 - 0.5, 13.2 - 0.4, 1.0, 0.8)) ]

    items = []
    for name, (x,y,w,h) in regions:
        rect = data_to_pixels_rect(x,y,w,h,img_w,img_h)
        items.append({'type':'region','name':name,'data_rect':(x,y,w,h),'rect':rect,'area':area(rect)})
    for name, (cx,cy,r) in gauges:
        x = cx - r
        y = cy - r
        w = 2*r
        h = 2*r
        rect = data_to_pixels_rect(x,y,w,h,img_w,img_h)
        items.append({'type':'gauge','name':name,'data_rect':(x,y,w,h),'rect':rect,'area':area(rect)})
    for name, (x,y,w,h) in cols:
        rect = data_to_pixels_rect(x,y,w,h,img_w,img_h)
        items.append({'type':'column','name':name,'data_rect':(x,y,w,h),'rect':rect,'area':area(rect)})

    # compute pairwise overlaps
    overlaps = []
    for i in range(len(items)):
        for j in range(i+1, len(items)):
            a = items[i]
            b = items[j]
            inter = intersect(a['rect'], b['rect'])
            if inter:
                inter_area = area(inter)
                # relative overlap metrics
                overlap_pct_a = inter_area / a['area'] if a['area']>0 else 0
                overlap_pct_b = inter_area / b['area'] if b['area']>0 else 0
                overlaps.append({'a':a['name'],'a_type':a['type'],'b':b['name'],'b_type':b['type'],'inter_area':inter_area,'a_area':a['area'],'b_area':b['area'],'overlap_pct_a':overlap_pct_a,'overlap_pct_b':overlap_pct_b,'inter_rect':inter})

    overlaps.sort(key=lambda x: x['inter_area'], reverse=True)

    out = {
        'image': image_path,
        'image_size': (img_w, img_h),
        'items': items,
        'overlaps': overlaps
    }

    out_path = os.path.splitext(image_path)[0] + '_collision_report.json'
    with open(out_path, 'w') as f:
        json.dump(out, f, indent=2)
    print(f'Wrote collision report: {out_path}')
    # also print a short summary
    if overlaps:
        print('Top overlaps:')
        for o in overlaps[:10]:
            print(f"{o['a']} ({o['a_type']}) <-> {o['b']} ({o['b_type']}): area={o['inter_area']} px, {o['overlap_pct_a']*100:.1f}% of {o['a']}, {o['overlap_pct_b']*100:.1f}% of {o['b']}")
    else:
        print('No overlaps detected')

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: python collision_report.py <path_to_png>')
        sys.exit(1)
    main(sys.argv[1])
