from pathlib import Path
p = Path('generate_fast_reports.py')
lines = p.read_text(encoding='utf-8').splitlines()
for i in range(860, 892):
    print(f"{i+1}: {repr(lines[i])}")
