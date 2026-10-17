import statistics
import sys
import time

from crayon import options as crayon_options

crayon_options(**{"crayon.enabled": True})
from diffobj.styles import PaletteOfStyles

def one():
    data = PaletteOfStyles().data
    names = []
    for color in data.dimnames["color.mode"]:
        for bright in data.dimnames["brightness"]:
            for fmt in data.dimnames["format"]:
                names.append(data[(fmt, bright, color)].__name__)
    return ",".join(names)

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
text = value if isinstance(value, str) else "\n".join(value)
sys.stdout.write("VALUE\n")
sys.stdout.write(text)
sys.stdout.write("\n<<<END>>>\n")
sys.stdout.write(f"MS {statistics.median(elapsed):.17g}\n")
