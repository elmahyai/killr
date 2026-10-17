import json
import statistics
import time
from pathlib import Path

from stringi._na import NA

from stringr.pattern import coll, fixed
from stringr.word import word


def plain(value):
    if value is NA:
        return None
    if isinstance(value, list):
        return [plain(item) for item in value]
    if isinstance(value, dict):
        return {key: plain(item) for key, item in value.items()}
    return value


from stringr.pattern import fixed
sentences = ["Jane saw a cat", "Jane sat down"]
text = "abc.def..123.4568.999"
lines = [
    repr(word(sentences, 1)),
    repr(word(sentences, 2)),
    repr(word(sentences, -1)),
    repr(word(sentences, 2, -1)),
    repr(word(sentences[0], [1, 2, 3], -1)),
    repr(word(sentences[0], 1, [1, 2, 3, 4])),
    repr(word(text, 1, sep=fixed(".."))),
    repr(word(text, 2, sep=fixed(".."))),
]
Path("/home/ahmed/killr_projects/killr/packages/stringr/docs/output/word-python.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")


def one():
    return {
        "first": word(["Jane saw a cat", "Jane sat down"], 1),
        "second": word(["Jane saw a cat", "Jane sat down"], 2),
        "last": word(["Jane saw a cat", "Jane sat down"], -1),
        "span": word(["Jane saw a cat", "Jane sat down"], 2, -1),
        "starts": word("Jane saw a cat", [1, 2, 3], -1),
        "ends": word("Jane saw a cat", 1, [1, 2, 3, 4]),
        "sep1": word("abc.def..123.4568.999", 1, sep=fixed("..")),
        "sep2": word("abc.def..123.4568.999", 2, sep=fixed("..")),
        "past": word("a b c", 4),
        "far": word("walk the moon", -5, -1),
        "double": word("a  b", [1, 2, 3]),
        "zero": word("a b", 0),
        "blank": word("", 1),
        "na": word(["a b", NA], 1),
        "nastart": word("a b c", NA),
        "regex": word("a-b-c", 2, sep="-"),
        "coll": word("a b c", 2, sep=coll(" ")),
        "empty": word([])
    }


value = plain(one())
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}, ensure_ascii=False))
