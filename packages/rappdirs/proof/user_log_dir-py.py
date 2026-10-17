import json
import statistics
import sys
import time

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/rappdirs")

from rappdirs.log import user_log_dir


def one():
    return [
        user_log_dir("rappdirs"),
        user_log_dir("R", os="mac"),
        user_log_dir("R", os="win"),
        user_log_dir("R", os="win", opinion=False, appauthor="Posit"),
        user_log_dir("rappdirs", os="unix"),
        user_log_dir("rappdirs", os="mac"),
        user_log_dir("rappdirs", version="%p-platform/%v"),
        user_log_dir("app", version="%V"),
        user_log_dir("app", version="%v"),
        user_log_dir("app", version="%%V"),
        user_log_dir(None),
        user_log_dir(""),
        user_log_dir(["a", "b"]),
    ]


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
