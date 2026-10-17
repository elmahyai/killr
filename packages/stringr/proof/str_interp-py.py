import json
import statistics
import time
from pathlib import Path

from stringr.interp import str_interp

out_dir = Path(__file__).resolve().parents[1] / "docs" / "output"
out_dir.mkdir(parents=True, exist_ok=True)
lines = [
    str_interp(
        "One value, ${value1}, and then another, ${value2*2}.",
        {"value1": 10, "value2": 20},
    )[0],
    str_interp(
        "User ${user_name} (account $[08d]{account}) has $$[.2f]{amount}.",
        {"user_name": "smbache", "account": 1337, "amount": 6.656},
    )[0],
]
(out_dir / "str_interp-python.txt").write_text("\n".join(lines) + "\n")


def one():
    return [
        str_interp(
            "One value, ${value1}, and then another, ${value2*2}.",
            {"value1": 10, "value2": 20},
        )[0],
        str_interp(
            "User ${user_name} (account $[08d]{account}) has $$[.2f]{amount}.",
            {"user_name": "smbache", "account": 1337, "amount": 6.656},
        )[0],
        str_interp(
            [
                "This particular line is so long that it is hard to write ",
                "without breaking the ${max_char}-char barrier!",
            ],
            {"max_char": 80},
        )[0],
    ]


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
