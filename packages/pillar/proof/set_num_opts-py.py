import json
import statistics
import time

from glue._text import r_character_double
from pillar.num import set_num_opts


def atom(value):
    if value is None:
        return "NA"
    if isinstance(value, float):
        return r_character_double(value)
    return str(value)


def encode(value):
    return ";".join(
        [
            ",".join(atom(item) for item in value.data),
            value.typeof,
            "/".join(value.classes),
            value.pillar,
            value.abbr,
        ]
    )


def one():
    return " || ".join(
        [
            encode(set_num_opts([1.0, 2.0], sigfig=2)),
            encode(set_num_opts([1, 2], sigfig=2)),
        ]
    )


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
