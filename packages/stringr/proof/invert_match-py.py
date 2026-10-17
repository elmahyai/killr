import json
import statistics
import time
from pathlib import Path

from stringi._na import NA, is_na
from stringr.locate import invert_match, str_locate_all


def canon(value):
    if value is NA or value is None:
        return None
    if isinstance(value, dict):
        return {key: canon(item) for key, item in value.items()}
    if isinstance(value, list):
        return [canon(item) for item in value]
    return value


def show(rows):
    lines = ["start end"]
    for row in rows:
        lines.append(" ".join("NA" if is_na(cell) else str(cell) for cell in row))
    return "\n".join(lines)


numbers = "1 and 2 and 4 and 456"
num_loc = str_locate_all(numbers, "[0-9]+")[0]
out = Path("/home/ahmed/killr_projects/killr/packages/stringr/docs/output/invert_match-python.txt")
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(show(invert_match(num_loc)) + "\n", encoding="utf-8")


def one():
    sentence = "1 and 2 and 4 and 456"
    locs = str_locate_all([sentence] * 200, "[0-9]+")
    return {
        "numbers": invert_match(str_locate_all(sentence, "[0-9]+")[0]),
        "many": [invert_match(loc) for loc in locs],
        "empty": invert_match([]),
        "miss": invert_match([[NA, NA]]),
        "gap": invert_match([[1, 2], [NA, NA]]),
    }


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

print(json.dumps({"value": canon(value), "median_ms": statistics.median(elapsed)}, ensure_ascii=False))
