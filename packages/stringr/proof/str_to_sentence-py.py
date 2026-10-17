import json
import statistics
import time
from pathlib import Path

from stringi._na import NA

from stringr.case import str_to_sentence


def plain(value):
    if value is NA:
        return None
    if isinstance(value, list):
        return [plain(item) for item in value]
    if isinstance(value, dict):
        return {key: plain(item) for key, item in value.items()}
    return value


lines = [repr(str_to_sentence("the quick brown dog")), repr(str_to_sentence("a Test. a second."))]
Path("/home/ahmed/killr_projects/killr/packages/stringr/docs/output/str_to_sentence-python.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")


def one():
    return {
        "dog": str_to_sentence("the quick brown dog"),
        "two": str_to_sentence("a Test. a second."),
        "hello": str_to_sentence("hello. world."),
        "na": str_to_sentence(NA),
        "empty": str_to_sentence([])
    }


value = plain(one())
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}, ensure_ascii=False))
