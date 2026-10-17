import json
import statistics
import sys
import time

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/rappdirs")

from rappdirs.appdir import app_dir


def one():
    ggplot2_app = app_dir("ggplot2", "hadley")
    return [
        ggplot2_app.cache(),
        ggplot2_app.log(),
        ggplot2_app.data(),
        ggplot2_app.config(),
        ggplot2_app.site_config(),
        ggplot2_app.site_data(),
        ggplot2_app.os,
    ]


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
