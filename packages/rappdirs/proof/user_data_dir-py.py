import json
import statistics
import sys
import time

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/rappdirs")

from rappdirs.data import user_data_dir


def one():
    return [
        user_data_dir("rappdirs"),
        user_data_dir("R", os="mac"),
        user_data_dir("rappdirs", roaming=True, os="win"),
        user_data_dir("rappdirs", roaming=False, os="win"),
        user_data_dir("R", os="win", appauthor="Posit"),
        user_data_dir("rappdirs", os="unix"),
        user_data_dir("rappdirs", os="mac"),
        user_data_dir("rappdirs", version="%p-platform/%v"),
        user_data_dir("app", version="%V"),
        user_data_dir("app", version="%v"),
        user_data_dir("app", version="%%V"),
        user_data_dir(None),
        user_data_dir(""),
        user_data_dir(["a", "b"]),
    ]


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
