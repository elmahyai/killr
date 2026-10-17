import json
import statistics
import time
import warnings
from pathlib import Path

from cli import ansi_strip
from cli._options import set_option
from stringi._na import NA, is_na
from stringr.view import str_view_all

set_option("cli.num_colors", 1)

out_dir = Path(__file__).resolve().parents[1] / "docs" / "output"
out_dir.mkdir(parents=True, exist_ok=True)
with warnings.catch_warnings():
    warnings.simplefilter("ignore", DeprecationWarning)
    shown = str(str_view_all(["abc", "def", "fghi"], "e"))
(out_dir / "str_view_all-python.txt").write_text(shown + "\n")


def spans_of(text):
    if text is None or text == "":
        return []
    spans = []
    original = 0
    index = 0
    chars = list(text)
    limit = len(chars)
    while index < limit:
        if chars[index] == "<":
            start = original + 1
            index += 1
            buf_n = 0
            while index < limit and chars[index] != ">":
                buf_n += 1
                index += 1
            if index < limit and chars[index] == ">":
                index += 1
            if buf_n == 0:
                spans.append([start, start - 1])
            else:
                spans.append([start, start + buf_n - 1])
            original += buf_n
        else:
            original += 1
            index += 1
    return spans


def plain(value):
    if is_na(value):
        return None
    stripped = ansi_strip(value)
    return "" if stripped is None else str(stripped)


def view_record(view):
    text = []
    spans = []
    for item in view:
        if is_na(item):
            text.append(None)
            spans.append([])
        else:
            shown_text = plain(item)
            text.append(shown_text)
            spans.append(spans_of(shown_text))
    return {"ids": list(view.ids), "text": text, "spans": spans}


def one():
    return view_record(str_view_all(["abc", "def", "fghi", NA], "e"))


with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    value = one()
    elapsed = []
    for _ in range(20):
        started = time.perf_counter()
        one()
        elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
