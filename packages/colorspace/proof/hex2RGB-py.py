import json
import statistics
import time

from colorspace.hex2rgb import hex2RGB

HEXES = [
    f"#{i:02X}{(255 - i):02X}{(i + 17) % 256:02X}" for i in range(256)
]


def _block(color):
    names = None if color.names is None else list(color.names)
    return {
        "space": color.space,
        "names": names,
        "columns": list(color.columns),
        "coords": color.coords.tolist(),
    }


def one():
    return {
        "plain": hex2RGB(
            [
                "#FF0000",
                "#00FF00",
                "#0000FF50",
                "#aabbcc",
                "#112233zzzz",
                "#aAbBcC",
            ]
        ),
        "named": hex2RGB({"red": "#FF0000", "blue": "#0000FF80"}),
        "encoded": hex2RGB(HEXES),
        "linear": hex2RGB(HEXES, gamma=True),
        "flag0": hex2RGB("#0A0000", gamma=0),
        "flag_true": hex2RGB("#0A0000", gamma="TRUE"),
        "flag2": hex2RGB("#0A0000", gamma=2),
    }


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

payload = {key: _block(color) for key, color in value.items()}
payload["median_ms"] = statistics.median(elapsed)
print(json.dumps(payload))
