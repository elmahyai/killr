import json
import statistics
import time
from evaluate import evaluate, is_recordedplot, trim_intermediate_plots

def one():
    ev = evaluate(["plot(1:3)", 'text(1, 1, "x")', 'text(1, 1, "y")'], envir={})
    trimmed = trim_intermediate_plots(ev)
    plots = [item for item in trimmed if is_recordedplot(item)]
    return [len(plots), len(plots[0].dl)]
value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
