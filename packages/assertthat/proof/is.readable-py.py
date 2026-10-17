import statistics
import time

import os
import tempfile
from assertthat import AssertThatError, is_readable

folder = tempfile.mkdtemp()
file = os.path.join(folder, "f")
open(file, "w").close()
try:
    is_readable("asdf-missing")
    miss = "NOERROR"
except AssertThatError as error:
    miss = error.args[0]

def one():
    return [is_readable(folder), is_readable(file)]

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(" ".join("1" if item else "0" for item in value))
print(miss)
print("MS")
print(f"{statistics.median(elapsed):.17g}")
