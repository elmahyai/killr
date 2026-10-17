import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from nlme.names import ListForm, Names
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


def one():
    pixel = load_pixel_csv()
    rs = reStruct({"Dog": "~day", "Side": "~1"}, data=pixel)
    pd = pdMat("~day", data=pixel)
    return (
        enc_list(Names(rs))
        + enc_chr(Names(pd))
        + enc_chr(Names("~day", data=pixel))
        + enc_chr(Names("~1"))
        + enc_chr(Names("~day"))
        + enc_list(Names(ListForm(["~day", "~1"]), data=pixel))
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
