import json
import statistics
import sys
import time
from io import StringIO
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from RColorBrewer.brewer import (
    brewer_pal_info,
    format_brewer_pal_info,
    format_brewer_pal_info_row,
)

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "output"
OUT.mkdir(parents=True, exist_ok=True)


def row_json(name):
    row = brewer_pal_info[name]
    return {
        "name": name,
        "maxcolors": row.maxcolors,
        "category": row.category,
        "colorblind": row.colorblind,
    }


def one():
    info = brewer_pal_info
    blues = brewer_pal_info["Blues"].maxcolors
    return info.maxcolors + [int(bool(v)) for v in info.colorblind] + [blues]


def capture_example():
    buffer = StringIO()
    buffer.write(format_brewer_pal_info(brewer_pal_info))
    buffer.write(format_brewer_pal_info_row(brewer_pal_info, "Blues"))
    buffer.write(f"[1] {brewer_pal_info['Blues'].maxcolors}\n")
    return buffer.getvalue()


(OUT / "brewer.pal.info-python.txt").write_text(capture_example())

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000.0)

cases = [
    {
        "label": "full",
        "rownames": brewer_pal_info.row_names(),
        "maxcolors": brewer_pal_info.maxcolors,
        "category": brewer_pal_info.category,
        "colorblind": [int(v) for v in brewer_pal_info.colorblind],
    },
    {"label": "Blues", "row": row_json("Blues")},
    {"label": "Blues_maxcolors", "value": brewer_pal_info["Blues"].maxcolors},
    {"label": "missing", "row": row_json("nope")},
]

print(json.dumps({"value": value, "cases": cases, "median_ms": statistics.median(elapsed)}))
