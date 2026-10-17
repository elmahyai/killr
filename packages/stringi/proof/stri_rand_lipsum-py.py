import json
import statistics
import time
from pathlib import Path

from stringi._na import NA


def plain(value):
    if value is NA:
        return None
    if isinstance(value, list):
        return [plain(item) for item in value]
    if isinstance(value, dict):
        return {key: plain(item) for key, item in value.items()}
    return value



from stringi.random import stri_rand_lipsum

x = stri_rand_lipsum(2, True)
Path("/home/ahmed/killr_projects/killr/packages/stringi/docs/output/stri_rand_lipsum-python.txt").write_text(
    f"stri_rand_lipsum(2, True) returns {len(x)} paragraphs.\n"
)


def one():
    drawn = stri_rand_lipsum(2, True)
    return {
        "n": len(drawn),
        "start": drawn[0].startswith("Lorem ipsum dolor sit amet"),
        "endings": all(item.endswith(".") for item in drawn),
        "no_newline": all("\n" not in item for item in drawn),
    }

value = plain(one())
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}, ensure_ascii=False))
