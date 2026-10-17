import statistics
import time

def one():
    from tools.session import find_gs_cmd
    bad = find_gs_cmd("no-such-gs-xyz")
    return find_gs_cmd() + "\n" + ("<none>" if bad == "" else bad) + "\n"

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(value, end="")
print("MS")
print(f"{statistics.median(elapsed):.17g}")
