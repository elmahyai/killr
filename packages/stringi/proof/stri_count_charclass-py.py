import json
import statistics
import time
from pathlib import Path

from stringi._na import NA
from stringi.charclass import stri_count_charclass

def canon(value):
    if value is NA:
        return None
    if isinstance(value, list):
        return [canon(item) for item in value]
    return value

tod = "\U000105C0"
emoji = "\U0001F600"
text = [
    "Abc def\t12",
    "  éÉ  ",
    tod + " 9",
    "a" + emoji + "b c",
    " \u00A0\t",
    "",
    NA,
] * 150
pat = ["\\p{L}", "\\p{N}", "\\p{WhiteSpace}", "\\p{Z}", "\\p{Lo}", "[:digit:]", "\\p{Emoji}"]

from stringi.charclass import stri_count_charclass
x = stri_count_charclass("stringi", "\\p{L}")
sentence = f'stri_count_charclass("stringi", "\\p{{L}}") returns {x[0]}.'

OUT = Path("/home/ahmed/killr_projects/killr/packages/stringi/docs/output/stri_count_charclass-python.txt")
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(sentence + "\n", encoding="utf-8")

def one():
    return stri_count_charclass(text, pat)

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

print(json.dumps({"value": canon(value), "median_ms": statistics.median(elapsed)}, ensure_ascii=False, separators=(",", ":")))
