import json
import statistics
import time
from pathlib import Path

from colorspace.protanomaly_cvd import protanomaly_cvd

OUT = Path(__file__).resolve().parents[1] / "docs" / "output"


def one():
    tables = protanomaly_cvd()
    names = sorted(tables.keys(), key=int)
    return {
        "names": names,
        "matrices": [tables[name].tolist() for name in names],
    }


def _format_list(tables) -> str:
    parts = []
    for name in sorted(tables, key=int):
        parts.append(f"$`{name}`")
        parts.append(_format_matrix(tables[name]))
        parts.append("")
    return "\n".join(parts) + "\n"


def _format_matrix(matrix) -> str:
    rows = [[float(value) for value in row] for row in matrix]
    decimals = any(not value.is_integer() for row in rows for value in row)
    cells = [[_format_number(value, decimals=decimals) for value in row] for row in rows]
    headers = [f"[,{col + 1}]" for col in range(3)]
    widths = [
        max(len(headers[col]), *(len(cells[row][col]) for row in range(3)))
        for col in range(3)
    ]
    gap = " "
    header = " " * 4 + "".join(gap + headers[col].rjust(widths[col]) for col in range(3))
    body = []
    for row in range(3):
        nums = "".join(gap + cells[row][col].rjust(widths[col]) for col in range(3))
        body.append(f"[{row + 1},]{nums}")
    return header + "\n" + "\n".join(body)


def _format_number(value: float, *, decimals: bool) -> str:
    if not decimals:
        if value == 0.0:
            return "0"
        return str(int(value))
    return f"{value:.6f}"


value = one()
OUT.mkdir(parents=True, exist_ok=True)
(OUT / "protanomaly_cvd-python.txt").write_text(
    _format_list(protanomaly_cvd()),
    encoding="utf-8",
)

elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

payload = {**value, "median_ms": statistics.median(elapsed)}
print(json.dumps(payload))
