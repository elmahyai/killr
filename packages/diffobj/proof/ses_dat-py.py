import os
import statistics
import time
from pathlib import Path

from diffobj import *
from diffobj.options import settings
a = list("abcdef")
b = ["b", "CC", "DD", "d", "f"]

def enc(rows):
    parts = []
    for row in rows:
        val = "NA" if row["val"] is None else row["val"]
        ida = "NA" if row["id_a"] is None else str(row["id_a"])
        idb = "NA" if row["id_b"] is None else str(row["id_b"])
        parts.append("|".join([row["op"], val, ida, idb]))
    return ";".join(parts)

def one():
    return ses_dat(a, b)

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(enc(value))
print(f"MS {statistics.median(elapsed):.17g}")
