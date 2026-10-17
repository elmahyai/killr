import statistics
import time

def one():
    from tools.nons3 import non_s3_methods
    known = "|".join(non_s3_methods("stats"))
    missing = "<none>" if non_s3_methods("nope") == [] else "BAD"
    return known + "\n" + missing + "\n" + str(len(non_s3_methods(None))) + "\n"

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(value, end="")
print("MS")
print(f"{statistics.median(elapsed):.17g}")
