from pathlib import Path
from PIL import Image

SRC = Path("assets/gidion-logo.png")
DST = Path("assets/gidion-logo.ico")

if not SRC.exists():
    raise SystemExit(f"Expected {SRC} — run this from the project root.")

img = Image.open(SRC).convert("RGBA")

if img.width != img.height:
    print(
        f"Warning: {SRC.name} is {img.width}x{img.height}, not square. "
        "Windows will stretch it into each icon size below, which can look "
        "distorted. A square source image (e.g. 512x512) gives cleaner results."
    )

img.save(DST, sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
print(f"Wrote {DST}")