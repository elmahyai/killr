"""Compare mclust.chull with R's chull on the battery written by chull-r.R.

Each case is compared as the ordered list of hull coordinates (what the plot
draws). A case matches when the two lists are identical. Writes
docs/output/chull-battery-compare.txt and prints the summary.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

PROOF = Path(__file__).resolve().parent
ROOT = PROOF.parent
OUT = ROOT / "docs" / "output"
sys.path.insert(0, str(ROOT))

from mclust.chull import chull  # noqa: E402


def parse(line: str) -> tuple[str, np.ndarray, list[int]]:
    tag, rest = (line.split(" ", 1) + [""])[:2] if line.startswith("ELLIPSE") else ("", line)
    left, right = rest.split("|")
    vals = [float(t) for t in left.split()]
    n = int(vals[0])
    x = np.array(vals[1:1 + n])
    y = np.array(vals[1 + n:1 + 2 * n])
    r_idx = [int(t) - 1 for t in right.split()]
    return tag, np.column_stack([x, y]), r_idx


def main() -> int:
    lines = (OUT / "chull-battery-r.txt").read_text().splitlines()
    total = same = 0
    failures: list[str] = []
    per_tag: dict[str, str] = {}
    for line in lines:
        tag, xy, r_idx = parse(line)
        py_idx = chull(xy).tolist()
        r_coords = [tuple(float(v) for v in xy[i]) for i in r_idx]
        py_coords = [tuple(float(v) for v in xy[i]) for i in py_idx]
        ok = r_coords == py_coords
        total += 1
        same += ok
        if tag:
            per_tag[tag] = "match" if ok else f"no ({len(py_coords)} vertices vs R {len(r_coords)})"
        elif not ok and len(failures) < 3:
            failures.append(f"n={len(xy)} R={r_coords} py={py_coords}")
    summary = [
        f"chull battery: {same} of {total} cases identical in vertex coordinates and order",
    ] + [f"  {k}: {v}" for k, v in per_tag.items()]
    summary.append("  random cases (mismatches shown only as the first three):")
    summary += [f"    {f}" for f in failures]
    text = "\n".join(summary) + "\n"
    (OUT / "chull-battery-compare.txt").write_text(text)
    print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
