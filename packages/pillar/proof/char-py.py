import json
import statistics
import time

from pillar.char import char, format_pillar_char_attr


def snap(x):
    data = x.data
    if not isinstance(data, list):
        data = [data]
    return {"data": data, "type": format_pillar_char_attr(x.pillar)}


def one():
    return [
        snap(char(["a", "bb"], min_chars=5, shorten="mid")),
        snap(char(["a", None])),
        snap(char("hello", min_chars=3, shorten="abbreviate")),
        snap(char("ab", shorten="back")),
        snap(char(["ab", "cd"], min_chars=2, shorten="front")),
    ]


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
