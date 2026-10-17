import json
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/htmltools")

from htmltools.escape import NA, htmlEscape

example = Path("/home/ahmed/killr_projects/killr/packages/htmltools/docs/output/htmlEscape-python.txt")
sample = "a < b & 'c'"
text_mode = htmlEscape(sample)[0]
attribute_mode = htmlEscape(sample, attribute=True)[0]
example.write_text(
    "htmlEscape(\"a < b & 'c'\") returns " + text_mode + ".\n"
    "htmlEscape(\"a < b & 'c'\", attribute = TRUE) returns " + attribute_mode + ".\n"
)

piece = [
    "a<b>c&d",
    "plain text",
    "say 'hi\"",
    "line1\r\nline2",
    NA,
    "",
    "caf\u00e9 < & > \u2603",
    "&amp; already",
    "it's a \"quote\"",
    ">>>",
    "a\tb",
    "\u00e9&\u00e9",
]
text = piece * 200
plain = ["nothing to escape"] * 200
quotes = "a'b\"c\r\n<&>"
numbers = [1e-4, 1e5, 10000.0, 0.00015, 2e5, NA, float("nan"), float("inf"), float("-inf"), -0.0, 1 / 3]


def plain_value(value):
    if value is NA:
        return None
    if isinstance(value, list):
        return [plain_value(item) for item in value]
    if isinstance(value, dict):
        return {key: plain_value(item) for key, item in value.items()}
    return value


def one():
    return {
        "text": htmlEscape(text),
        "attr": htmlEscape(text, True),
        "plain": htmlEscape(plain),
        "numbers": htmlEscape(numbers),
        "integer": htmlEscape([100000, 1, NA]),
        "logical": htmlEscape([True, False, NA]),
        "mixed": htmlEscape(["a<", 1e5, True, 100000]),
        "flags": {
            "false": htmlEscape(quotes, False),
            "true": htmlEscape(quotes, True),
            "zero": htmlEscape(quotes, 0),
            "two": htmlEscape(quotes, 2),
            "false_word": htmlEscape(quotes, "false"),
            "t_word": htmlEscape(quotes, "T"),
        },
        "empty": htmlEscape(None),
        "na": htmlEscape(NA),
    }


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"median_ms": statistics.median(elapsed), "value": plain_value(value)}))
