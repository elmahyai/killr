import os
import sys
import time
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from conflicted import conflict_prefer

def run():
    return conflict_prefer("median", "stats", losers=["base"], quiet=True)

run()
times = []
for _ in range(20):
    started = time.perf_counter()
    run()
    times.append((time.perf_counter() - started) * 1000)
print("result=None")
print(f"translated_ms={sorted(times)[9:11][0] + (sorted(times)[9:11][1] - sorted(times)[9:11][0]) / 2:.9f}")
