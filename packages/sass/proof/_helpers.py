"""Fixed-input proof runner for the small sass helper exports."""
import statistics
import time
from pathlib import Path


def run(name, python_call, r_value, rendered):
    times = []
    result = python_call()  # untimed
    for _ in range(20):
        start = time.perf_counter()
        result = python_call()
        times.append(time.perf_counter() - start)
    translated = rendered(result)
    max_abs_diff = 0.0 if translated == r_value else float("inf")
    out = Path(__file__).parent / f"{name}_proof.txt"
    out.write_text(
        f"function: {name}\nmatch: {max_abs_diff == 0.0}\n"
        f"max_abs_diff: {max_abs_diff}\nr_ms: unavailable (R proof environment)\n"
        f"translated_ms: {statistics.median(times)*1000:.8g}\n"
        "speedup: unavailable (R proof environment)\n"
        f"r_output: {r_value}\npython_output: {translated}\n",
        encoding="utf-8",
    )
    return out
