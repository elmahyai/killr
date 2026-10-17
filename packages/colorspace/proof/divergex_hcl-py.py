import json
import statistics
import time

from colorspace.divergex_hcl import divergex_hcl


def _json_vec(values):
    return [None if value is None else str(value) for value in values]


def one():
    return {
        "default": divergex_hcl(7),
        "geyser": divergex_hcl(7, palette="Geyser"),
        "armyrose": divergex_hcl(7, palette="ArmyRose"),
        "rdylbu": divergex_hcl(11, palette="RdYlBu"),
        "tropic": divergex_hcl(7, palette="Tropic"),
        "zissou": divergex_hcl(7, palette="Zissou 1"),
        "override_h1": divergex_hcl(7, palette="Geyser", h1=200),
        "odd_n": divergex_hcl(11, palette="Spectral"),
        "even_n": divergex_hcl(10, palette="Spectral"),
        "single": divergex_hcl(1, palette="PuOr"),
        "rev": divergex_hcl(7, palette="Geyser", rev=True),
        "alpha": divergex_hcl(
            5, palette="Geyser", alpha=(1, 0.5, 0.25, 0.5, 1)
        ),
        "explicit_alpha1": divergex_hcl(3, palette="Geyser", alpha=1),
        "no_fixup": divergex_hcl(7, palette="Geyser", fixup=False, c1=120),
        "bulk": divergex_hcl(256, palette="Temps"),
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
