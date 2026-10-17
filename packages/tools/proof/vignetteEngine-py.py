import statistics
import time

def one():
    from tools.vignette import vignette_engine
    e = vignette_engine("Sweave")
    try:
        vignette_engine("nope")
        miss = ""
    except ValueError as exc:
        miss = str(exc)
    try:
        vignette_engine("Sweave", weave=lambda: 1, tangle=lambda: 2, package="tools")
        locked = ""
    except ValueError as exc:
        locked = str(exc)
    vignette_engine("demo", weave=lambda: 1, tangle=lambda: 2, package="tools")
    got = vignette_engine("tools::demo")
    return f"{e['name']} {e['package']} {e['pattern']}\n{miss}\n{locked}\n{got['name']} {got['package']} {got['pattern']}\n"

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(value, end="")
print("MS")
print(f"{statistics.median(elapsed):.17g}")
