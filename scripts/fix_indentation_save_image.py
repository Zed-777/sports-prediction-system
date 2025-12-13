from pathlib import Path

p = Path('generate_fast_reports.py')
lines = p.read_text(encoding='utf-8').splitlines()
# find def save_image
start = None
for idx, line in enumerate(lines):
    if line.strip().startswith('def save_image('):
        start = idx
        break
if start is None:
    print('save_image not found')
    raise SystemExit(1)
# find end: next line that starts with 4 spaces and 'def ' (another method) at same class level
end = len(lines)
for idx in range(start+1, len(lines)):
    candidate = lines[idx]
    if candidate.startswith('    def ') and not candidate.startswith('        '):
        end = idx
        break
# adjust indentation for lines between start+1 and end
changed = False
for idx in range(start+1, end):
    current_line = lines[idx]
    # skip empty lines
    if current_line.strip()=='' or current_line.lstrip().startswith('#'):
        continue
    # count leading spaces
    leading = len(current_line) - len(current_line.lstrip(' '))
    if leading < 8:
        lines[idx] = ' '*(8-leading) + current_line
        changed = True
if changed:
    p.write_text('\n'.join(lines)+"\n", encoding='utf-8')
    print('Adjusted indentation for save_image')
else:
    print('No changes needed')
