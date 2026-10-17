"""Series shipped with changepoint 2.3."""

from pathlib import Path

import numpy as np

_DIR = Path(__file__).resolve().parent / "data"


def _frame(name, columns):
    raw = np.load(_DIR / f"{name}.npz")
    return {column: raw[column] for column in columns}


def ftse100():
    raw = np.load(_DIR / "ftse100.npz")
    return {"date": raw["date"], "value": raw["value"]}


def HC1():
    return np.load(_DIR / "HC1.npy")


def Lai2005fig3():
    return _frame("Lai2005fig3", ["Spot", "CH", "POS.start", "POS.end", "GBM31"])


def Lai2005fig4():
    return _frame("Lai2005fig4", ["Spot", "CH", "POS.start", "POS.end", "GBM29"])


def wave_c44137():
    return np.load(_DIR / "wave.c44137.npy")
