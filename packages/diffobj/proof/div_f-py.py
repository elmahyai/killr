import os
import statistics
import time
from pathlib import Path

from diffobj import *
from diffobj.options import settings
def one():
    return div_f("ex2", {"color": "green", "font-family": "arial"})(list("ABCDE"))

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print("|".join(value))
print(f"MS {statistics.median(elapsed):.17g}")
