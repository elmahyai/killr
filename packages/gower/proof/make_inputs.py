"""Write the fixed inputs shared by proof_r.R and proof_python.py.

Run from the repository root:

    python3 packages/gower/proof/make_inputs.py

Writes packages/gower/proof/data/x.csv (800 rows, 8 columns) and
packages/gower/proof/data/y.csv (400 rows, 7 columns). NA is written as NA.
Doubles are written with repr(), which round-trips exactly.
"""

import csv
import os

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
LEVELS = ["a", "b", "c", "d"]


def x_rows(n=800):
    rows = []
    for idx in range(n):
        i = idx + 1
        rows.append([
            None if i % 97 == 0 else ((i * 37) % 101) / 10,      # x1 dbl
            None if i % 13 == 0 else (i * 5) % 11,               # x2 int
            None if i % 29 == 0 else (i % 3 == 0),               # x3 lgl
            None if i % 31 == 0 else LEVELS[(i * 7) % 4],        # x4 factor
            None if i % 41 == 0 else ["ab", "cd", "ef", "gh"][(i * 3) % 4],  # x5 chr
            ((i * 13) % 23) / 4,                                  # x6 dbl
            (i * i) % 7,                                          # x7 int
            (i % 5) / 2,                                          # x8 dbl (skipped)
        ])
    return rows


def y_rows(n=400):
    rows = []
    for idx in range(n):
        j = idx + 1
        rows.append([
            None if j % 89 == 0 else ((j * 29) % 97) / 10,       # y1 dbl
            None if j % 17 == 0 else (j * 3) % 11,               # y2 int
            None if j % 23 == 0 else (j % 2 == 0),               # y3 lgl
            None if j % 37 == 0 else LEVELS[(j * 5) % 4],        # y4 factor
            None if j % 43 == 0 else ["ab", "cd", "ef", "gh", "ij"][(j * 2) % 5],  # y5 chr
            ((j * 11) % 19) / 3,                                  # y6 dbl
            (j * j + 1) % 9,                                      # y7 int
        ])
    return rows


def fmt(v):
    if v is None:
        return "NA"
    if isinstance(v, bool):
        return "TRUE" if v else "FALSE"
    if isinstance(v, float):
        return repr(v)
    return str(v)


def write(path, names, rows):
    with open(path, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(names)
        for r in rows:
            w.writerow([fmt(v) for v in r])


def main():
    os.makedirs(DATA, exist_ok=True)
    write(os.path.join(DATA, "x.csv"), [f"x{k}" for k in range(1, 9)], x_rows())
    write(os.path.join(DATA, "y.csv"), [f"y{k}" for k in range(1, 8)], y_rows())
    print("wrote", os.path.join(DATA, "x.csv"), "and", os.path.join(DATA, "y.csv"))


if __name__ == "__main__":
    main()
