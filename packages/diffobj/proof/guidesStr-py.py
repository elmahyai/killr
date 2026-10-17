import statistics
import sys
import time

from crayon import options as crayon_options

crayon_options(**{"crayon.enabled": True})
from diffobj.guides import guidesStr

def one():
    lines = ["List of 2", " $ a: num 1", " $ b:List of 1", "  ..$ c: num 2"]
    g = guidesStr({"a": 1}, lines)
    return "EMPTY" if not g else ",".join(map(str, g))

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
