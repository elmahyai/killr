import json
import statistics
import string
import time

from cli._options import options as cli_options

cli_options(**{"cli.num_colors": 8, "cli.unicode": True})

from pillar._options import options as pillar_options
from pillar.parts import new_pillar_title, new_pillar_type, pillar_component

pillar_options(
    **{"pillar.bold": False, "pillar.subtle": True, "pillar.min_title_chars": 20}
)


def one():
    title = pillar_component(new_pillar_title("letters"))
    kind = pillar_component(new_pillar_type(list(string.ascii_lowercase)))
    return {
        "title_width": title.width,
        "title_min_width": title.min_width,
        "type_width": kind.width,
        "type_min_width": kind.min_width,
    }


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
