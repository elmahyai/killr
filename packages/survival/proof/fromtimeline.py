import csv
import statistics
import time
from pathlib import Path

from survival.fromtimeline import Categorical, fromtimeline

_LEVELS = ["censor", "normal", "1-4", "4+", "death"]
_CSV = Path(__file__).with_name("fromtimeline_pdata.csv")


def _flt(text):
    return float("nan") if text == "NA" else float(text)


def _fac(text):
    return None if text == "NA" else text


def _load_pdata():
    rows = list(csv.DictReader(_CSV.open()))
    return {
        "id": [int(row["id"]) for row in rows],
        "day": [_flt(row["day"]) for row in rows],
        "age": [_flt(row["age"]) for row in rows],
        "bili": [_flt(row["bili"]) for row in rows],
        "albumin": [_flt(row["albumin"]) for row in rows],
        "edema": [_flt(row["edema"]) for row in rows],
        "ast": [_flt(row["ast"]) for row in rows],
        "bstat": Categorical([_fac(row["bstat"]) for row in rows], _LEVELS),
        "bstat2": Categorical([_fac(row["bstat2"]) for row in rows], _LEVELS),
    }


def _serialize(frame):
    lines = ["|".join(frame.names)]
    for name, col in zip(frame.names, frame.columns):
        if isinstance(col, Categorical):
            col = col.values
        if hasattr(col, "tolist"):
            col = col.tolist()
        tokens = []
        for value in col:
            if value is None or (isinstance(value, float) and value != value):
                tokens.append("NA")
            elif isinstance(value, float):
                tokens.append(f"{value:.17g}")
            else:
                tokens.append(str(value))
        lines.append(",".join(tokens))
    return lines


def one():
    return _serialize(fromtimeline("Surv(day, bstat) ~ .", _load_pdata(), id="id"))


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print("\n".join(value))
print("MS")
print(f"{statistics.median(elapsed):.17g}")
