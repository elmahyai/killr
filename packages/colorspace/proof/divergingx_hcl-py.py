import json
import statistics
import time

from colorspace.divergingx_hcl import divergingx_hcl


def _json_vec(values):
    return [None if value is None else str(value) for value in values]


def one():
    return {
        "default": divergingx_hcl(7),
        "geyser": divergingx_hcl(7, palette="Geyser"),
        "armyrose": divergingx_hcl(7, palette="ArmyRose"),
        "rdylbu": divergingx_hcl(11, palette="RdYlBu"),
        "tropic": divergingx_hcl(7, palette="Tropic"),
        "zissou": divergingx_hcl(7, palette="Zissou 1"),
        "override_h1": divergingx_hcl(7, palette="Geyser", h1=200),
        "odd_n": divergingx_hcl(11, palette="Spectral"),
        "even_n": divergingx_hcl(10, palette="Spectral"),
        "single": divergingx_hcl(1, palette="PuOr"),
        "rev": divergingx_hcl(7, palette="Geyser", rev=True),
        "alpha": divergingx_hcl(
            5, palette="Geyser", alpha=(1, 0.5, 0.25, 0.5, 1)
        ),
        "explicit_alpha1": divergingx_hcl(3, palette="Geyser", alpha=1),
        "no_fixup": divergingx_hcl(7, palette="Geyser", fixup=False, c1=120),
        "bulk": divergingx_hcl(256, palette="Temps"),
    }


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

payload = {key: _json_vec(val) for key, val in value.items()}
payload["median_ms"] = statistics.median(elapsed)
print(json.dumps(payload))
