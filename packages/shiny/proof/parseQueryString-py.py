import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from shiny.query import format_query, parseQueryString
from shiny.values import NA_character_, ShinyError, Vector

STRINGS = [
    "?foo=1&bar=b%20a%20r",
    "?foo=1&bar=b+a%20r&b+a%20z=baz&=nokey&novalue=&=&noequal&end=end",
    "foo=1&bar=b",
    "?foo=1&bar=b",
    "?&a=1&&b=2&",
    "a[i1][j1]=x&b[i1][j1]=y&b[i2][j1]=z",
    "",
    "?",
    "a=b=c",
    "a=%2B%26%3D",
    "k=%C3%A9",
    "k=%E2%82%AC",
    "a=%",
    "a=%2",
    "a=%zz",
    "a=%00",
    "a=%61%00%62",
    "k=A%41B%zzC%41",
    "k=%4%41",
    "k=%%41",
    "k=%41%zz%41",
    "k=%FF",
    "k=%C3",
    "k=%0A",
    "a[b]=1&c=2",
    "a[b][c]=2&a[b]=1",
    "a[b]=1&a[b][c]=2",
    "a=9&a[b]=1",
    "a%5Bb%5D=z",
    "a[b+c]=x",
    "a=1&a=2",
    "a[b]c=1",
    "\u00e9=1",
    "k=+%41",
]


def grab(fn):
    try:
        return format_query(fn())
    except ShinyError as exc:
        return "ERR " + str(exc)


def one():
    parts = []
    for text in STRINGS:
        parts.append(grab(lambda text=text: parseQueryString(text)))
        parts.append(grab(lambda text=text: parseQueryString(text, nested=True)))
    parts.append(grab(lambda: parseQueryString(None)))
    parts.append(grab(lambda: parseQueryString(None, nested=True)))
    parts.append(grab(lambda: parseQueryString(Vector([], "character"))))
    parts.append(grab(lambda: parseQueryString(Vector(["a=1", "b=2"], "character"))))
    parts.append(grab(lambda: parseQueryString(1)))
    parts.append(grab(lambda: parseQueryString(Vector([NA_character_], "character"))))
    return "\n".join(parts)


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
shown = value.replace("\n", " / ")
print("VALUE " + shown)
print(f"MS {statistics.median(elapsed):.17g}")
