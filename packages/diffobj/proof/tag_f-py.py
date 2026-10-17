import os
import statistics
import time
from pathlib import Path

from diffobj import *
from diffobj.options import settings
def one():
    return tag_f("div", "ex1")(list("ABCDE"))

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print("|".join(value))
print(f"MS {statistics.median(elapsed):.17g}")
