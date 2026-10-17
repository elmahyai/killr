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
    "match_classes",
    "/home/ahmed/killr_projects/killr/packages/e1071/e1071/match_classes.py",
)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
match_classes = _mod.match_classes


def one():
    tab = [[10, 1, 2], [1, 10, 1], [2, 1, 10]]
    result = match_classes(tab, method="exact", verbose=False)
    return [float(result[str(index + 1)]) for index in range(3)]


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
