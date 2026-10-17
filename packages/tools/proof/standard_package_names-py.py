import statistics
import time

def one():
    from tools.session import standard_package_names
    std = standard_package_names()
    return ",".join(std["base"]) + " || " + ",".join(std["recommended"]) + "\n"

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(value, end="")
print("MS")
print(f"{statistics.median(elapsed):.17g}")
