import json
import statistics
import time
import matplotlib.pyplot as plt
from evaluate import plot, remove_hooks, set_hooks

def one():
    box = {"n": 0}
    def first():
        box["n"] += 1
    def second():
        box["n"] += 10
    set_hooks({"before.plot.new": first})
    set_hooks({"before.plot.new": second})
    plot(1)
    remove_hooks({"before.plot.new": first})
    remove_hooks({"before.plot.new": second})
    plt.close("all")
    return box["n"]
value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
