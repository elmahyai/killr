import os
import statistics
import time
from pathlib import Path

from diffobj import *
from diffobj.options import settings
import hashlib

def one():
    return diffobj_js()

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(hashlib.md5(Path(value).read_bytes()).hexdigest())
print(f"MS {statistics.median(elapsed):.17g}")
