import statistics
import time
from tools.file_ext import NA_character_, file_ext

def show(value):
    if value.__class__.__name__ == "NA":
        return "NA"
    if value == "":
        return "<empty>"
    return value

def one():
    values = file_ext(["a.txt", "a.tar.gz", ".hidden", "file.", "file.c++", "a.é", "x.Y_z", "foo/bar.txt.bak", NA_character_])
    return [show(item) for item in values] + [show(file_ext(1.5)), show(file_ext(1)), "<logical0>" if file_ext(None) == [] else "BAD"]

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(" ".join(value))
print("MS")
print(f"{statistics.median(elapsed):.17g}")
