import statistics
import time

def one():
    import tempfile
    from tools.index import read_00index
    path = tempfile.mktemp()
    with open(path, "w", encoding="utf-8") as handle:
        handle.write("foo     A description\n        continued\n\nbar\tThe bar\n")
    rows = read_00index(path)
    return "|".join(f"{a}={b}" for a, b in rows) + "\n"

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(value, end="")
print("MS")
print(f"{statistics.median(elapsed):.17g}")
