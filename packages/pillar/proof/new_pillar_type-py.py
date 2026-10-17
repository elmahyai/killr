import json
import statistics
import string
import time

from cli._options import options as cli_options

cli_options(**{"cli.num_colors": 8, "cli.unicode": True})

from pillar._options import options as pillar_options
from pillar._vec import Factor
from pillar.parts import new_pillar_type

pillar_options(**{"pillar.bold": False, "pillar.subtle": True})


def one():
    kind = new_pillar_type(list(string.ascii_lowercase))
    return {
        "chr": new_pillar_type("a").format(),
        "fct": new_pillar_type(Factor(["a"])).format(),
        "width": kind.width,
        "min_width": kind.min_width,
    }


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
