import os
import statistics
import time
from pathlib import Path

from diffobj import *
from diffobj.options import settings
def one():
    item = auto_context(0, 3)
    return [item.min, item.max]

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print("|".join(str(part) for part in value))
print(f"MS {statistics.median(elapsed):.17g}")
