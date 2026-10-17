import json
import statistics
import sys
import time

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/rappdirs")

from rappdirs.site import site_config_dir


def _add(out, value):
    if isinstance(value, list):
        out.extend(value)
    else:
        out.append(value)


def one():
    out = []
    _add(out, site_config_dir("rappdirs"))
    _add(out, site_config_dir("R", os="mac"))
    _add(out, site_config_dir("R", os="win", appauthor="Posit"))
    _add(out, site_config_dir("rappdirs", os="unix"))
    _add(out, site_config_dir("rappdirs", os="unix", multipath=True))
    _add(out, site_config_dir("app", version="%V"))
    _add(out, site_config_dir("app", version="%v"))
    _add(out, site_config_dir(None))
    _add(out, site_config_dir(""))
    _add(out, site_config_dir(["a", "b"]))
    return out


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
