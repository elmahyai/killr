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



from stringi.wrap import stri_wrap

s = (
    "Lorem ipsum dolor sit amet, consectetur adipisicing elit. Proin "
    "nibh augue, suscipit a, scelerisque sed, lacinia in, mi. Cras vel "
    "lorem. Etiam pellentesque aliquet tellus."
)
Path("/home/ahmed/killr_projects/killr/packages/stringi/docs/output/stri_wrap-python.txt").write_text(
    f"stri_wrap(s, 20, 0) returns {len(stri_wrap(s, 20, 0, locale='en_US'))} lines.\n"
)


def one():
    return {
        "greedy": stri_wrap(s, 20, 0, locale="en_US"),
        "dynamic": stri_wrap(s, 20, 2, locale="en_US"),
        "indent": stri_wrap(
            s, 24, 0, indent=2, exdent=4, prefix="> ", initial="* ", normalize=False, locale="en_US"
        ),
        "ws": stri_wrap("hello   world  wide", 10, 0, whitespace_only=True, normalize=False, locale="en_US"),
        "cjk": stri_wrap("一一 一一 一", 4, 0, use_length=False, normalize=False, locale="en_US"),
        "emoji": stri_wrap("a😀 b cd", 3, 0, normalize=False, locale="en_US"),
        "norm": stri_wrap("hello\nworld  there", 10, 0, normalize=True, locale="en_US"),
        "missing": stri_wrap(["ab cd ef", NA], 4, 0, normalize=False, locale="en_US"),
    }

value = plain(one())
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}, ensure_ascii=False))
