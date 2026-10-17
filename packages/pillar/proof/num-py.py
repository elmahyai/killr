import json
import statistics
import time

from glue._text import r_character_double
from pillar.num import num


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
            encode(num([1, 2.5, None])),
            encode(num([1, 2], sigfig=4, label="kg")),
            encode(num(1, digits=2, notation="sci")),
            encode(num(1, notation="si", fixed_exponent=-3, scale=10, label="m")),
        ]
    )


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
