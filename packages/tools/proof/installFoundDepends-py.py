import statistics
import time

def one():
    from tools.defunct import install_found_depends
    try:
        install_found_depends("x")
        return "\n"
    except RuntimeError as exc:
        return str(exc) + "\n"

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(value, end="")
print("MS")
print(f"{statistics.median(elapsed):.17g}")
