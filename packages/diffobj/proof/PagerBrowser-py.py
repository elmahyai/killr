import statistics
import sys
import time

from crayon import options as crayon_options

crayon_options(**{"crayon.enabled": True})
from diffobj.pager import PagerBrowser

def one():
    p = PagerBrowser()
    mb = "NA" if getattr(p.make_blocking, "kind", None) else ("TRUE" if p.make_blocking else "FALSE")
    return "|".join([p.class_name, p.file_ext, mb])

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
