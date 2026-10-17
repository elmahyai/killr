import statistics
import time
from pathlib import Path

from PIL import Image

from fontawesome.fa_png import fa_png

output = Path(__file__).parents[1] / "docs" / "output" / "fa_png-py.png"
output.parent.mkdir(parents=True, exist_ok=True)

fa_png("r-project", file=output, fill="red")
elapsed = []
for _ in range(20):
    t0 = time.perf_counter()
    fa_png("r-project", file=output, fill="red")
    elapsed.append(time.perf_counter() - t0)

with Image.open(output) as image:
    pixels = list(image.convert("RGBA").getdata())
    print(f"py_ms {statistics.median(elapsed) * 1000:.17g}")
    print(f"dimensions {image.width}x{image.height}")
    print(f"pixels {len(pixels)}")
