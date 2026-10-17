import json
import statistics
import time
import matplotlib.pyplot as plt
from evaluate import plot, remove_hooks, set_hooks

def one():
    box = []
    def count():
        box.append(1)
    hooks = {"before.plot.new": count}
    set_hooks(hooks)
    plot(1)
    remove_hooks(hooks)
    plot(1)
    plt.close("all")
    return len(box)
value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
