"""Datasets shipped with tseries. Each file is the series R stores in data/."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np


class SeriesData:
    def __init__(self, values, start, end, frequency, names):
        self.values = values
        self.start = start
        self.end = end
        self.frequency = frequency
        self.names = names


def load(name):
    path = Path(__file__).resolve().parent / "data" / f"{name}.json"
    payload = json.loads(path.read_text())
    values = np.array(payload["data"], dtype=float)
    return SeriesData(
        values,
        float(payload["start"]),
        float(payload["end"]),
        float(payload["frequency"]),
        list(payload["names"]),
    )


def USeconomic():
    return load("USeconomic")


def NelPlo():
    return load("NelPlo")


def bev():
    return load("bev")


def camp():
    return load("camp")


def ice_river():
    return load("ice.river")


def nino():
    return load("nino")


def tcm():
    return load("tcm")


def tcmd():
    return load("tcmd")
