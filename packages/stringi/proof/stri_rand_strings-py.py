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



from stringi.random import stri_rand_strings

x = stri_rand_strings(4, 5, "[a-z]")
lengths = ", ".join(str(len(item)) for item in x)
Path("/home/ahmed/killr_projects/killr/packages/stringi/docs/output/stri_rand_strings-python.txt").write_text(
    f"stri_rand_strings(4, 5, '[a-z]') returns {len(x)} strings of length {lengths}.\n"
)


def one():
    drawn = stri_rand_strings(4, [3, 5], ["[0-9]", "[abc]"])
    return {
        "n": len(drawn),
        "lengths": [len(item) for item in drawn],
        "digits": all(len(item) == 3 and set(item) <= set("0123456789") for item in (drawn[0], drawn[2])),
        "letters": all(len(item) == 5 and set(item) <= set("abc") for item in (drawn[1], drawn[3])),
        "empty_n": len(stri_rand_strings(0, 3)),
        "na_length": stri_rand_strings(1, NA)[0] is NA,
    }

value = plain(one())
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}, ensure_ascii=False))
