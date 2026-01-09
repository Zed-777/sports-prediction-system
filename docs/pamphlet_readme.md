Pamphlet (Quick Start)
======================

Files created:

- `docs/pamphlet.json` — Structured pamphlet content (human-readable & machine-friendly)
- `docs/pamphlet.png` — Simple PNG image of the pamphlet for quick distribution

How to regenerate PNG:

1. Ensure Pillow is installed:

   ```powershell
   pip install pillow
   ```

2. Run the generator:

   ```powershell
   python scripts/generate_pamphlet_png.py
   ```

If you want a different layout or higher-resolution image, I can update `scripts/generate_pamphlet_png.py` to use different fonts, colors, or multi-column layout.
