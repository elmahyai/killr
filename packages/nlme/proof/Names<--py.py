import statistics
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from nlme.names import Names, set_names
from nlme.pdmat import pdMat
from nlme.restruct import load_pixel_csv, reStruct


def enc_chr(x):
    if x is None:
        return [-1.0]
    if isinstance(x, str):
        x = [x]
    out = [float(len(x))]
    for s in x:
        out.extend(float(ord(ch)) for ch in s)
        out.append(0.0)
    return out


def enc_list(lst):
    out = []
    for item in lst:
        out.extend(enc_chr(item))
    return out


def safe(fn):
    try:
        return fn()
    except (ValueError, NotImplementedError):
        return [-2.0]


def one():
    pixel = load_pixel_csv()
    rs = reStruct({"Dog": "~day", "Side": "~1"}, data=pixel)
    pd = pdMat("~day", data=pixel)
    pd_perm = set_names(pd, ["day", "(Intercept)"])
    initialized = pdMat(
        np.array([[2.0, 0.5], [0.5, 1.0]]),
        nam=("a", "b"),
        pdClass="pdLogChol",
    )
    initialized_perm = set_names(initialized, ["b", "a"])
    pd_suffix = set_names(pd, ["day.(Intercept)", "(Intercept)"])
    pd_null = set_names(pd, None)
    rs_perm = set_names(rs, [["(Intercept)"], ["day", "(Intercept)"]])

    def bad_names():
        return enc_chr(Names(set_names(pd, ["foo", "(Intercept)"])))

    def bad_length():
        return enc_chr(Names(set_names(pd, ["a"])))

    def bad_rs_length():
        return enc_list(Names(set_names(rs, [["a"]])))

    return (
        enc_chr(Names(pd_perm))
        + enc_chr(Names(pd_suffix))
        + enc_chr(Names(pd_null))
        + enc_chr(Names(initialized_perm))
        + enc_list(Names(rs_perm))
        + safe(bad_names)
        + safe(bad_length)
        + safe(bad_rs_length)
    )


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(
    '{"value":[%s],"median_ms":%.17g}'
    % (",".join("%.17g" % float(part) for part in value), statistics.median(elapsed))
)
