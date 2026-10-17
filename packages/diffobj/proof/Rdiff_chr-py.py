import statistics
import sys
import time

from crayon import options as crayon_options

crayon_options(**{"crayon.enabled": True})
from diffobj.rdiff import Rdiff_chr

def one():
    return "\n".join(Rdiff_chr(list("abcde"), list("ABCDE"), silent=True))

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
