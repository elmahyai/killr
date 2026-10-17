import statistics
import time

def one():
    from tools.defunct import package_dependencies
    try:
        package_dependencies()
        msg = "NOERROR"
    except RuntimeError as error:
        msg = str(error)
    return msg + "\n"

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(value, end="")
print("MS")
print(f"{statistics.median(elapsed):.17g}")
