import json
import math
import statistics
import sys
import time
import warnings
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from RColorBrewer.brewer import BrewerPalError, brewer_pal

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "output"
OUT.mkdir(parents=True, exist_ok=True)

ORDER = (
    "BrBG", "PiYG", "PRGn", "PuOr", "RdBu", "RdGy", "RdYlBu", "RdYlGn", "Spectral",
    "Accent", "Dark2", "Paired", "Pastel1", "Pastel2", "Set1", "Set2", "Set3",
    "Blues", "BuGn", "BuPu", "GnBu", "Greens", "Greys", "Oranges", "OrRd",
    "PuBu", "PuBuGn", "PuRd", "Purples", "RdPu", "Reds", "YlGn", "YlGnBu", "YlOrBr", "YlOrRd",
)
MAX = {
    "BrBG": 11, "PiYG": 11, "PRGn": 11, "PuOr": 11, "RdBu": 11, "RdGy": 11,
    "RdYlBu": 11, "RdYlGn": 11, "Spectral": 11, "Accent": 8, "Dark2": 8,
    "Paired": 12, "Pastel1": 9, "Pastel2": 8, "Set1": 9, "Set2": 8, "Set3": 12,
    "Blues": 9, "BuGn": 9, "BuPu": 9, "GnBu": 9, "Greens": 9, "Greys": 9,
    "Oranges": 9, "OrRd": 9, "PuBu": 9, "PuBuGn": 9, "PuRd": 9, "Purples": 9,
    "RdPu": 9, "Reds": 9, "YlGn": 9, "YlGnBu": 9, "YlOrBr": 9, "YlOrRd": 9,
}


def one():
    return brewer_pal(7, "Greens")


def run(label, n, name):
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        try:
            colors = brewer_pal(n, name)
        except BrewerPalError as exc:
            warn = "".join(str(item.message) for item in caught) or None
            return {"label": label, "colors": None, "warning": warn, "error": str(exc)}
    warn = "".join(str(item.message) for item in caught) or None
    return {"label": label, "colors": colors, "warning": warn, "error": None}


value = one()
(OUT / "brewer.pal-python.txt").write_text(
    'brewer.pal(7, "Greens") returns ' + " ".join(value) + ".\n"
)

elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000.0)

cases = []
for name in ORDER:
    limit = MAX[name]
    for n in range(3, limit + 1):
        cases.append(run(f"{name}:{n}", n, name))
    cases.append(run(f"{name}:max+1", limit + 1, name))

cases.extend(
    [
        run("min:1:Blues", 1, "Blues"),
        run("min:2:Blues", 2, "Blues"),
        run("min:0:Blues", 0, "Blues"),
        run("min:-1:Set1", -1, "Set1"),
        run("min:-Inf:Blues", -math.inf, "Blues"),
        run("min:2.999:Greens", 2.999, "Greens"),
        run("max:100:Blues", 100, "Blues"),
        run("max:Inf:Blues", math.inf, "Blues"),
        run("max:1e20:Set3", 1e20, "Set3"),
        run("trunc:3.9:Greens", 3.9, "Greens"),
        run("trunc:8.2:Blues", 8.2, "Blues"),
        run("trunc:8.999:Blues", 8.999, "Blues"),
        run("int:Greens", 7, "Greens"),
        run("vec:Greens", [7], "Greens"),
        run("namevec:Greens", 7, ["Greens"]),
        run("true:Blues", True, "Blues"),
        run("false:Reds", False, "Reds"),
        run("bad:nope", 5, "nope"),
        run("bad:Blue", 4, "Blue"),
        run("bad:blues", 4, "blues"),
        run("bad:empty", 4, ""),
        run("bad:NA", 5, "NA"),
        run("null:name", 5, None),
        run("null:n", None, "Blues"),
        run("char:n", "7", "Greens"),
        run("len:n", [4, 5], "Blues"),
        run("len:name", 4, ["Blues", "Reds"]),
        run("na:n", float("nan"), "Blues"),
        run("nan:n", float("nan"), "Set1"),
    ]
)

print(json.dumps({"value": value, "cases": cases, "median_ms": statistics.median(elapsed)}))
