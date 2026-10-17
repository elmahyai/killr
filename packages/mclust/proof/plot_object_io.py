"""Reads the fitted-object JSON that proof/plot_object_io.R writes.

Both sides read the same file. A numeric node comes back as a NumPy array
with its dim (column-major values, so the reshape uses order "F"). G, d and n
come back as floats, and a one-element string as a str.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import numpy as np

PROOF = Path(__file__).resolve().parent


def _num(node: dict[str, Any] | None) -> Any:
    if node is None:
        return None
    vals = [math.nan if v is None else float(v) for v in node["v"]]
    arr = np.asarray(vals, dtype=float)
    if node.get("dim") is None:
        return arr
    return arr.reshape(tuple(node["dim"]), order="F")


def _chr(node: dict[str, Any] | None) -> Any:
    if node is None:
        return None
    vals = list(node["v"])
    return vals[0] if len(vals) == 1 and node.get("dim") is None else vals


def read_mclust_object(path: Path | str) -> dict[str, Any]:
    j = json.loads(Path(path).read_text())
    bic = j["BIC"]
    variance = {}
    for name, node in j["parameters"]["variance"].items():
        variance[name] = _chr(node) if node["t"] == "c" else _num(node)
    obj: dict[str, Any] = {
        "data": _num(j["data"]),
        "colnames": _chr(j["colnames"]),
        "d": int(_num(j["d"])[0]),
        "G": int(_num(j["G"])[0]),
        "n": int(_num(j["n"])[0]),
        "modelName": _chr(j["modelName"]),
        "classification": _num(j["classification"]),
        "uncertainty": _num(j["uncertainty"]),
        "z": _num(j["z"]),
        "BIC": {
            "values": _num(bic["values"]),
            "G": _num(bic["G"]),
            "modelNames": _chr(bic["modelNames"]),
            "rownames": _chr(bic["rownames"]),
            "colnames": _chr(bic["colnames"]),
            "returnCodes": _num(bic["returnCodes"]),
        },
        "parameters": {
            "pro": _num(j["parameters"]["pro"]),
            "mean": _num(j["parameters"]["mean"]),
            "variance": variance,
        },
        "class": _chr(j["class"]),
    }
    if j.get("density") is not None:
        obj["density"] = _num(j["density"])
    return obj
