import json
import statistics
import sys
import time

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/rappdirs")

from rappdirs.config import user_config_dir


def one():
    return [
        user_config_dir("rappdirs"),
        user_config_dir("R", os="mac"),
        user_config_dir("rappdirs", roaming=True, os="win"),
        user_config_dir("rappdirs", roaming=False, os="win"),
        user_config_dir("R", os="win", appauthor="Posit"),
        user_config_dir("rappdirs", os="unix"),
        user_config_dir("rappdirs", os="mac"),
        user_config_dir("rappdirs", version="%p-platform/%v"),
        user_config_dir("app", version="%V"),
        user_config_dir("app", version="%v"),
        user_config_dir("app", version="%%V"),
        user_config_dir(None),
        user_config_dir(""),
        user_config_dir(["a", "b"]),
    ]


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
