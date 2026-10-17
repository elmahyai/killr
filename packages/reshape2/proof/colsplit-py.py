"""Check colsplit against the reshape2 1.4.5 example and a fixed split."""

import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from reshape2.colsplit import colsplit
from reshape2.frame import is_factor


def format_cell(storage, value, levels):
    if storage == "factor":
        if value is None:
            return "NA"
        return str(levels[int(value) - 1])
    if value is None:
        return "NA"
    if storage == "logical":
        return "TRUE" if value else "FALSE"
    if storage == "integer":
        return str(int(value))
    if storage == "double":
        if value != value:
            return "NaN"
        if value == float("inf"):
            return "Inf"
        if value == float("-inf"):
            return "-Inf"
        return format(float(value), ".17g")
    return str(value)


def format_table(df):
    names = [name for name, _ in df.columns]
    rows = []
    rendered = []
    for name, column in df.columns:
        levels = column.attributes.get("levels", []) if is_factor(column) else None
        storage = "factor" if is_factor(column) else column.storage
        rendered.append([format_cell(storage, value, levels) for value in column.values])
    width = [max(len(name), *(len(item) for item in col)) for name, col in zip(names, rendered)]
    header = "  ".join(name.rjust(w) for name, w in zip(names, width))
    lines = [header]
    for index in range(df.nrows):
        lines.append("  ".join(rendered[col][index].rjust(width[col]) for col in range(len(names))))
    return "\n".join(lines)


def format_str(df):
    lines = [f"data.frame: {df.nrows} obs. of {len(df.columns)} variables:"]
    for name, column in df.columns:
        if is_factor(column):
            levels = column.attributes.get("levels", [])
            labels = ["NA" if code is None else levels[int(code) - 1] for code in column.values]
            shown = " ".join(repr(label) if label != "NA" else "NA" for label in labels[:8])
            lines.append(f" $ {name}: factor {shown}")
        elif column.storage == "character":
            shown = " ".join("NA" if value is None else repr(value) for value in column.values[:8])
            lines.append(f" $ {name}: chr {shown}")
        elif column.storage == "integer":
            shown = " ".join("NA" if value is None else str(int(value)) for value in column.values[:8])
            lines.append(f" $ {name}: int {shown}")
        elif column.storage == "double":
            shown = " ".join("NA" if value is None else format(float(value), ".17g") for value in column.values[:8])
            lines.append(f" $ {name}: num {shown}")
        else:
            lines.append(f" $ {name}: {column.storage}")
    return "\n".join(lines)


out = Path(__file__).resolve().parents[1] / "docs" / "output" / "colsplit-python.txt"
out.parent.mkdir(parents=True, exist_ok=True)
example = colsplit(["a_1", "a_2", "b_2", "c_3"], "_", ["trt", "time"])
out.write_text(format_table(example) + "\n" + format_str(example) + "\n", encoding="utf-8")

n = 8000
string = []
for k in range(n):
    if k % 17 == 0:
        string.append(None)
    elif k % 19 == 0:
        string.append(f"g{k % 11}")
    else:
        string.append(f"g{k % 11}_{k % 100}_{(k % 50) / 2:.1f}")


def one():
    return colsplit(string, "_", ["group", "time", "amount"])


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)


def emit(df):
    print(f"NROW {df.nrows}")
    for name, column in df.columns:
        if is_factor(column):
            levels = column.attributes.get("levels", [])
            print("COL " + name + " factor " + "|".join(str(level) for level in levels))
            vals = ["NA" if code is None else str(levels[int(code) - 1]) for code in column.values]
        elif column.storage == "character":
            print("COL " + name + " character ")
            vals = ["NA" if item is None else str(item) for item in column.values]
        elif column.storage == "integer":
            print("COL " + name + " integer ")
            vals = ["NA" if item is None else str(int(item)) for item in column.values]
        elif column.storage == "logical":
            print("COL " + name + " logical ")
            vals = ["NA" if item is None else ("TRUE" if item else "FALSE") for item in column.values]
        else:
            print("COL " + name + " double ")
            vals = []
            for item in column.values:
                if item is None:
                    vals.append("NA")
                elif item != item:
                    vals.append("NaN")
                elif item == float("inf"):
                    vals.append("Inf")
                elif item == float("-inf"):
                    vals.append("-Inf")
                else:
                    vals.append(format(float(item), ".17g"))
        print("\t".join(vals))


print(f"MEDIAN_MS {statistics.median(elapsed):.17g}")
emit(value)
