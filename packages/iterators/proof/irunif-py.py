import math
import statistics
import sys
import time
import warnings
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from iterators.core import IteratorError, iter, nextElem
from iterators.irunif import NA, irunif, set_seed


def fmt_num(values):
    if len(values) == 0:
        return "EMPTY"
    parts = []
    for value in values:
        if value is NA:
            parts.append("NA")
            continue
        number = float(value)
        if number == 0.0 and math.copysign(1.0, number) < 0:
            parts.append("-0")
            continue
        if math.isnan(number):
            parts.append("NaN")
        elif math.isinf(number):
            parts.append("Inf" if number > 0 else "-Inf")
        else:
            parts.append(format(number, ".17g"))
    return ",".join(parts)


def step(it):
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        try:
            value = nextElem(it)
            text = "NUM:" + fmt_num(value)
        except IteratorError as exc:
            text = "ERR:" + exc.message.replace("\n", "<NL>")
    if caught:
        notes = ",".join(str(item.message) for item in caught)
        text = "W:" + notes + ";" + text
    return text


def build(fn):
    try:
        fn()
        return "OK"
    except IteratorError as exc:
        return "ERR:" + exc.message.replace("\n", "<NL>")


def one():
    parts = []

    def add(*fields):
        for field in fields:
            if isinstance(field, (list, tuple)):
                parts.extend(field)
            else:
                parts.append(field)

    set_seed(1)
    it = irunif(5)
    add(step(it), step(it))

    set_seed(1)
    it = irunif(1, count=3)
    add(step(it), step(it), step(it), step(it))

    set_seed(1)
    it = irunif(1, min=2, max=5, count=2)
    add(step(it), step(it), step(it))

    set_seed(1)
    add(step(irunif(2, min=[0, 10], max=[1, 11])))

    set_seed(1)
    add(step(irunif(3, min=[0, 5, 0], max=1)))

    set_seed(1)
    add(step(irunif(3, min=[0, 4, 0], max=[1, 4, 1])))

    set_seed(1)
    add(step(irunif(2, min=3, max=3)), step(irunif(1)))

    set_seed(1)
    add(step(irunif(2, min=5, max=1)), step(irunif(1)))

    set_seed(1)
    add(step(irunif(2, min=[])), step(irunif(1)))

    add(step(irunif(0, min=5, max=1)))
    add(step(irunif(0, min=[])))
    add(step(irunif([])))
    add(step(irunif(0.9)))
    add(step(irunif(-0.0)))
    add(step(irunif(False)))
    add(step(irunif(0, min="a")))

    add(step(irunif(-1)))
    add(step(irunif(-0.1)))
    add(step(irunif(float("nan"))))
    add(step(irunif(float("nan"))))
    add(step(irunif(float("inf"))))
    add(step(irunif(float("-inf"))))
    add(step(irunif(None)))
    add(step(irunif("a")))
    add(step(irunif("a", min=None)))
    add(step(irunif("")))
    add(step(irunif("-1")))
    add(step(irunif("1e20")))
    add(step(irunif(2**52 + 1)))

    set_seed(1)
    add(step(irunif("3")))
    set_seed(1)
    add(step(irunif(" 2")))
    set_seed(1)
    add(step(irunif("1.9")))
    set_seed(1)
    add(step(irunif(2.2)))
    set_seed(1)
    add(step(irunif(1.9)))
    set_seed(1)
    add(step(irunif([1, 2, 3])))
    set_seed(1)
    add(step(irunif(True)))
    set_seed(1)
    add(step(irunif([True, False, True])))
    set_seed(1)
    add(step(irunif(["a", "b"])))
    set_seed(1)
    add(step(irunif(complex(2.9, 1))))
    add(step(irunif(complex(-1, 2))))
    add(step(irunif(complex(1, float("nan")))))
    add(step(irunif(complex(float("nan"), 0))))
    add(step(irunif(b"\x01")))
    set_seed(1)
    add(step(irunif(b"\x01\x02\x03")))
    add(step(irunif(b"")))

    set_seed(1)
    add(step(irunif(4, min=[0, 10], max=[1, 20, 30])))
    set_seed(1)
    add(step(irunif(2, min=[0, 1, 2], max=10)))
    set_seed(1)
    add(step(irunif(2, min=True, max=False)))
    add(step(irunif(1, min=None)))
    add(step(irunif(1, min="0")))
    add(step(irunif(1, min=complex(1, 0))))
    set_seed(1)
    add(step(irunif(1, min=float("nan"))))
    set_seed(1)
    add(step(irunif(1, max=float("inf"))))
    set_seed(1)
    add(step(irunif(1, min=-0.0, max=-0.0)))
    set_seed(1)
    add(step(irunif(1, mi=2, ma=5)))
    set_seed(1)
    add(step(irunif(n=5)))

    add(step(irunif(1, m=0)))
    add(step(irunif(m=0)))
    add(step(irunif(1, max=2, ma=3)))
    add(step(irunif(1, foo=1, bar=2)))
    add(step(irunif(1, 0, 1, 5, 6)))
    add(step(irunif()))
    add(step(irunif(min=0)))
    add(step(irunif(1, minimum=0)))

    add(build(lambda: irunif(1, count="a")))
    add(build(lambda: irunif(1, count=[1, 2])))
    add(build(lambda: irunif(1, count=True)))
    add(build(lambda: irunif(1, count=False)))
    add(build(lambda: irunif(1, count=None)))
    add(build(lambda: irunif(1, count=[])))
    add(build(lambda: irunif(1, count="")))

    set_seed(1)
    it = irunif(1, count=float("nan"))
    add(step(it))
    set_seed(1)
    it = irunif(1, count=float("nan"))
    add(step(it))
    it = irunif(1, count=0)
    add(step(it))
    it = irunif(1, count=-1)
    add(step(it))
    it = irunif(1, count=float("-inf"))
    add(step(it))

    set_seed(1)
    it = irunif(1, count=1.5)
    add(step(it), step(it), step(it))

    set_seed(1)
    it = irunif(1, count=float("inf"))
    add(step(it), step(it), step(it))

    set_seed(1)
    it = irunif(1)
    add(step(it), step(it))

    set_seed(1)
    it = irunif(count=2)
    add(step(it), step(it), step(it))

    set_seed(1)
    it = irunif(n="a", count=1)
    add(step(it), step(it))

    set_seed(1)
    it = irunif(1, coun=3)
    add(step(it), step(it))

    set_seed(1)
    p = irunif(1, count=2)
    q = irunif(1, count=1)
    add(step(p), step(q), step(p), step(q), step(p))

    set_seed(1)
    base = irunif(1, count=1)
    same = "SAME" if iter(base) is base else "DIFF"
    add(same, step(base), step(base))

    set_seed(1)
    it = irunif(1, count=[1])
    add(step(it), step(it))

    set_seed(1)
    it = irunif(1, count=1)
    add(step(it), step(it), step(it))

    return "|".join(parts)


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print("VALUE " + value)
print(f"MS {statistics.median(elapsed):.17g}")
