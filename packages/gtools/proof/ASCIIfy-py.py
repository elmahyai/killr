import json
import statistics
import sys
import time
import warnings

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/gtools")
from gtools.asciiify import ASCIIfy


def json_str(text):
    parts = []
    for char in text:
        cp = ord(char)
        if cp == 34:
            parts.append('\\"')
        elif cp == 92:
            parts.append("\\\\")
        elif cp == 10:
            parts.append("\\n")
        elif cp == 13:
            parts.append("\\r")
        elif cp == 9:
            parts.append("\\t")
        elif cp < 32 or cp == 127:
            parts.append(f"\\u{cp:04x}")
        else:
            parts.append(char)
    return '"' + "".join(parts) + '"'


def flat(values):
    return "|".join(json_str(item) for item in values)


def one():
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        cities1 = ASCIIfy(["S\u00e3o Paulo", "Reykjav\u00edk"], 1)
        cities2 = ASCIIfy(["S\u00e3o Paulo", "Reykjav\u00edk"], 2)
        athens = ASCIIfy("\u0391\u03b8\u03ae\u03bd\u03b1")
        bulk1 = ASCIIfy(
            ["a", "S\u00e3o Paulo", "\u0391\u03b8\u03ae\u03bd\u03b1", "caf\u00e9", "z\\x", ""],
            bytes=1,
        )
        bulk2 = ASCIIfy(
            ["a", "S\u00e3o Paulo", "\u0391\u03b8\u03ae\u03bd\u03b1", "caf\u00e9", "z\\x", ""],
            bytes=2,
        )
        singles = [
            ASCIIfy("z", 1),
            ASCIIfy("\u00e9", 1),
            ASCIIfy("\u00e9", 2),
            ASCIIfy("\u0391", 1),
            ASCIIfy("\u0391", 2),
            ASCIIfy("\u03fe", 1),
            ASCIIfy("\u03fe", 2),
        ]
    if isinstance(cities1, str):
        cities1 = [cities1]
    if isinstance(cities2, str):
        cities2 = [cities2]
    if isinstance(athens, str):
        athens = [athens]
    if isinstance(bulk1, str):
        bulk1 = [bulk1]
    if isinstance(bulk2, str):
        bulk2 = [bulk2]
    return [*cities1, *cities2, *athens, *bulk1, *bulk2, *singles]


value = flat(one())
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
