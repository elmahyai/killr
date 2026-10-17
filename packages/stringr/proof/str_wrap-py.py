import json
import statistics
import time
from pathlib import Path

from stringi._na import NA

from stringr.wrap import str_wrap


def plain(value):
    if value is NA:
        return None
    if isinstance(value, list):
        return [plain(item) for item in value]
    if isinstance(value, dict):
        return {key: plain(item) for key, item in value.items()}
    return value


from pathlib import Path
from stringr.pattern import fixed
from stringr.word import word
thanks = "\n".join(Path("/usr/share/R/doc/THANKS").read_text(encoding="utf-8").splitlines())
thanks = word(thanks, 1, 3, sep=fixed("\n\n"))[0]
chunks = [
    str_wrap(thanks)[0],
    str_wrap(thanks, width=40)[0],
    str_wrap(thanks, width=60, indent=2)[0],
    str_wrap(thanks, width=60, exdent=2)[0],
    str_wrap(thanks, width=0, exdent=2)[0],
]
Path("/home/ahmed/killr_projects/killr/packages/stringr/docs/output/str_wrap-python.txt").write_text("\n".join(chunks) + "\n", encoding="utf-8")


def one():
    return {
        "blank": str_wrap(["", " ", "  a  "]),
        "zero": str_wrap("a b c d e", 0),
        "slash": str_wrap("a/b", width=0, whitespace_only=False),
        "space": str_wrap("a/b", width=0, whitespace_only=True),
        "indent": str_wrap("one two three four", width=10, indent=2, exdent=1),
        "na": str_wrap(["hello world there", NA], width=8),
        "empty": str_wrap([])
    }


value = plain(one())
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}, ensure_ascii=False))
