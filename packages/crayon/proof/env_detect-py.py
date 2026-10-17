"""Generic Python side of the terminal-detection proof.

Args: output path, setup code (may be ""), expression to time.
The same environment as the R side is inherited (see run_env_detect.py).
"""

from __future__ import annotations

import statistics
import sys
import time

import crayon

out_path, setup, expr_text = sys.argv[1], sys.argv[2], sys.argv[3]

namespace = {name: getattr(crayon, name) for name in crayon.__all__}
if setup:
    exec(compile(setup, "<setup>", "exec"), namespace)
code = compile(expr_text, "<expr>", "eval")


def hex_chr(text: str) -> str:
    return text.encode("utf-8").hex()


def flatten(value):
    if isinstance(value, (list, tuple)):
        for item in value:
            yield from flatten(item)
    else:
        yield value


# One untimed call.
value = eval(code, namespace)

elapsed = []
for _ in range(20):
    started = time.perf_counter()
    value = eval(code, namespace)
    elapsed.append(time.perf_counter() - started)

lines = [f"py_ms {statistics.median(elapsed) * 1000:.17g}"]
for item in flatten(value):
    if isinstance(item, str):
        lines.append(f"chr {hex_chr(item)}")
    else:
        lines.append(f"num {float(item):.17g}")

with open(out_path, "w", encoding="utf-8") as handle:
    handle.write("\n".join(lines) + "\n")
