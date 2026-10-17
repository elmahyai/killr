import importlib.util
import json
import statistics
import sys
import time

sys.path[:0] = [
    "/home/ahmed/killr_projects/killr/packages/e1071",
    "/home/ahmed/killr_projects/killr/packages/boot",
    "/home/ahmed/killr_projects/killr/packages/zoo",
]
_spec = importlib.util.spec_from_file_location(
    "compare_matched_classes",
    "/home/ahmed/killr_projects/killr/packages/e1071/e1071/compare_matched_classes.py",
)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
compareMatchedClasses = _mod.compareMatchedClasses


def one():
    x = [[1], [2], [1], [2], [1]]
    y = [[1], [1], [2], [2], [2]]
    r = compareMatchedClasses(x, y, verbose=False)
    return [r["diag"][0][0], r["kappa"][0][0], r["rand"][0][0], r["crand"][0][0]]


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
