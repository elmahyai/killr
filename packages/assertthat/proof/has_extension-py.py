import statistics
import time
from assertthat import has_extension

def one():
    return [has_extension("a/b.txt", "txt"), has_extension("/tmp/foo", ""), has_extension("file.", ""), has_extension("file.c++", "c++"), has_extension(".hidden", "hidden"), has_extension("a.tar.gz", "gz"), has_extension("a.é", "é"), has_extension("x.Y_z", "Y_z")]

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(" ".join("1" if item else "0" for item in value))
print("MS")
print(f"{statistics.median(elapsed):.17g}")
