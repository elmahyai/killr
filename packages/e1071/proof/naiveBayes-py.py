import json
import statistics
import sys
import time

sys.path[:0] = ["/home/ahmed/killr_projects/killr/packages/e1071"]
from e1071.naive_bayes import flatten_naive_bayes, naive_bayes

CASE_COLUMNS = ["height", "color", "fast"]


def one():
    x = {
        "height": [170, 160, 175, float("nan"), 180, 165],
        "color": ["red", "blue", "red", "red", "blue", "red"],
        "fast": [True, False, True, False, True, False],
    }
    y = ["A", "B", "A", "B", "A", "B"]
    fit = naive_bayes(x, y, laplace=1)
    return flatten_naive_bayes(fit, CASE_COLUMNS)


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
