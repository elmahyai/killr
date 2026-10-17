import json
import statistics
import time

from cli import options as cli_options
from progressr.cli_handlers import pbcol

cli_options(**{"cli.num_colors": 1, "width": 80})


def one():
    return {
        "half": pbcol(fraction=0.5, msg="Hi", width=20),
        "full": pbcol(fraction=1, msg="", width=12),
        "long": pbcol(fraction=0.5, msg="x" * 200, width=40),
    }


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
value["median_ms"] = statistics.median(elapsed)
print(json.dumps(value, ensure_ascii=False))
