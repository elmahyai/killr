import json
import statistics
import time
from pathlib import Path

import numpy as np

from colorspace.deutanomaly_cvd import deutanomaly_cvd
from colorspace.interpolate_cvd_transform import interpolate_cvd_transform
from colorspace.protanomaly_cvd import protanomaly_cvd
from colorspace.tritanomaly_cvd import tritanomaly_cvd

OUT = Path(__file__).resolve().parents[1] / "docs" / "output"
STEPS = np.arange(101, dtype=np.float64) / 100.0


def one():
    tritan = tritanomaly_cvd()
    protan = protanomaly_cvd()
    deutan = deutanomaly_cvd()
    return {
        "example": interpolate_cvd_transform(tritan, 0.6),
        "zero": interpolate_cvd_transform(tritan, 0),
        "full": interpolate_cvd_transform(tritan, 1),
        "above": interpolate_cvd_transform(protan, 1.5),
        "below": interpolate_cvd_transform(protan, -0.2),
        "mid": interpolate_cvd_transform(protan, 0.5),
        "quarter": interpolate_cvd_transform(protan, 0.25),
        "three_tenths": interpolate_cvd_transform(deutan, 0.3),
        "third": interpolate_cvd_transform(deutan, 1 / 3),
        "frac": interpolate_cvd_transform(tritan, 0.55),
        "bulk_tritan": [interpolate_cvd_transform(tritan, step) for step in STEPS],
        "bulk_protan": [interpolate_cvd_transform(protan, step) for step in STEPS],
        "bulk_deutan": [interpolate_cvd_transform(deutan, step) for step in STEPS],
    }


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
    return header + "\n" + "\n".join(body) + "\n"


def _format_number(value: float, *, decimals: bool) -> str:
    if not decimals:
        if value == 0.0:
            return "0"
        return str(int(value))
    return f"{value:.6f}"


value = one()
OUT.mkdir(parents=True, exist_ok=True)
(OUT / "interpolate_cvd_transform-python.txt").write_text(
    _format_matrix(value["example"]),
    encoding="utf-8",
)

elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

payload = {key: np.asarray(item).tolist() for key, item in value.items()}
payload["median_ms"] = statistics.median(elapsed)
print(json.dumps(payload))
