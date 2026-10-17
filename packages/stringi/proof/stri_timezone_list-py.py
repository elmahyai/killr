import json
import statistics
import time
from pathlib import Path

from stringi.datetime import stri_timezone_list

shown = stri_timezone_list(region="PL")
Path(
    "/home/ahmed/killr_projects/killr/packages/stringi/docs/output/stri_timezone_list-python.txt"
).write_text(
    'stri_timezone_list(region = "PL") returns ' + " and ".join(shown) + ".\n"
)


def one():
    return {
        "all": stri_timezone_list(),
        "pl": stri_timezone_list(region="PL"),
        "off1": stri_timezone_list(offset=1),
        "off55": stri_timezone_list(offset=5.5),
        "us": stri_timezone_list(region="US", offset=-10),
        "empty": stri_timezone_list(region=""),
    }


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}, ensure_ascii=False))
