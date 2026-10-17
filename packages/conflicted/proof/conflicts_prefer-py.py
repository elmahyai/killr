import os, sys, time
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from conflicted import conflicts_prefer
def run():
    return conflicts_prefer("stats.median", _quiet=True)
run(); times = []
for _ in range(20):
    started = time.perf_counter(); run()
    times.append((time.perf_counter() - started) * 1000)
times.sort()
print("result=None")
print(f"translated_ms={(times[9] + times[10]) / 2:.9f}")
