import json
import statistics
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path("/home/ahmed/killr_projects/killr")
sys.path[:0] = [
    str(ROOT / "packages" / "deSolve"),
    str(ROOT / "crates" / "lagvalue"),
]

from deSolve.lagvalue import lagvalue, restore_hist  # noqa: E402


def _load_snapshot():
    import subprocess

    r_script = ROOT / "packages" / "deSolve" / "proof" / "lagvalue-r.R"
    snap_path = ROOT / "packages" / "deSolve" / "proof" / "lagvalue-hist.json"
    if not snap_path.exists():
        subprocess.run(["R", "--slave", "-f", str(r_script)], check=True)
    return json.loads(snap_path.read_text())


def one(snapshot):
    restore_hist(snapshot)
    tq = np.array([0.5, 1, 1.5, 2.5, 5, 10, 15, 19.5], dtype=float)
    out = []
    for tt in tq:
        out.extend(np.asarray(lagvalue(float(tt)), dtype=float).reshape(-1))
    for tt in tq:
        out.append(float(lagvalue(float(tt), 2)))
    out.extend(np.asarray(lagvalue(7.25), dtype=float).reshape(-1))
    out.extend(np.asarray(lagvalue(7.25, [1, 2]), dtype=float).reshape(-1))
    return out


def main():
    snapshot = _load_snapshot()
    value = one(snapshot)
    elapsed = []
    for _ in range(20):
        started = time.perf_counter()
        one(snapshot)
        elapsed.append((time.perf_counter() - started) * 1000)
    r_path = ROOT / "packages" / "deSolve" / "proof" / "lagvalue-r-out.json"
    if not r_path.exists():
        import subprocess

        subprocess.run(["R", "--slave", "-f", str(ROOT / "packages" / "deSolve" / "proof" / "lagvalue-r.R")], check=True)
    r_payload = json.loads(r_path.read_text())
    r_value = r_payload["value"]
    diff = max(abs(a - b) for a, b in zip(value, r_value))
    payload = {
        "value": value,
        "median_ms": statistics.median(elapsed),
        "max_abs_diff": diff,
        "matches": bool(diff <= 1e-8),
        "r_median_ms": r_payload["median_ms"],
    }
    print(json.dumps(payload))


if __name__ == "__main__":
    main()
