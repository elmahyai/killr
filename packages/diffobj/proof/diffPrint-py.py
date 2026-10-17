import statistics
import sys
import time

from crayon import options as crayon_options

crayon_options(**{"crayon.enabled": True})
from diffobj.diff import diffPrint

def one():
    letters = list("abcdefghijklmnopqrstuvwxyz")
    current = [item for item in letters if item != "e"]
    diff = diffPrint(letters, current, format="raw", pager="off", tar_banner="letters", cur_banner="letters[-5]")
    return "\n".join(diff.lines)

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
