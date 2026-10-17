import os, sys, time
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from conflicted import conflict_prefer_all, register_package, reset
register_package("stats", {"median": object(), "mean": object(), "sd": object()})
register_package("base", {"median": object(), "mean": object(), "sd": object()})
def run():
    return conflict_prefer_all("stats", losers=["base"], quiet=True)
run(); times = []
for _ in range(20):
    started = time.perf_counter(); run()
    times.append((time.perf_counter() - started) * 1000)
times.sort()
print("result=None")
print(f"translated_ms={(times[9] + times[10]) / 2:.9f}")
