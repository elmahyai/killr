import statistics
import sys
import time

sys.path[:0] = ["/home/ahmed/killr_projects/killr/packages/stringdist"]
from stringdist.printable_ascii import printable_ascii


def as_num(value):
    if isinstance(value, list):
        return [as_num(item) for item in value]
    if value is None:
        return None
    return 1.0 if value else 0.0


def flatten(parts):
    out = []
    for part in parts:
        if isinstance(part, list):
            out.extend(flatten(part))
        else:
            out.append(part)
    return out


def one():
    ouml = "\u00f6"
    x = ["Motorhead", "Mot" + ouml + "rhead"]
    return flatten(
        [
            as_num(printable_ascii(x)),
            as_num(printable_ascii("abc\r")),
            as_num(printable_ascii(None)),
            as_num(printable_ascii([None, "abc"])),
            as_num(printable_ascii([None, "abc"])),
            as_num(printable_ascii([])),
            as_num(printable_ascii("\t")),
            as_num(printable_ascii("hello\tworld")),
            as_num(printable_ascii("")),
            as_num(printable_ascii(["", " ", "A", "!"])),
            as_num(printable_ascii("Mot\u00f6rhead")),
            as_num(printable_ascii("abc\n")),
            as_num(printable_ascii("ASCII only 123")),
            as_num(
                printable_ascii(
                    " !\"#$%&'()*+,./:;<=>?@[\\]^_`{|}~-"
                )
            ),
            as_num(printable_ascii(["Robert", "rupert", "Rubin"])),
            as_num(printable_ascii("\rhello")),
            as_num(printable_ascii("hello\r")),
        ]
    )


def fmt(value):
    if value is None:
        return "null"
    if value != value:
        return '"NaN"'
    if value == float("inf"):
        return '"Inf"'
    if value == float("-inf"):
        return '"-Inf"'
    return format(float(value), ".17g")


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
text = ",".join(fmt(item) for item in value)
print('{"value":[%s],"median_ms":%.17g}' % (text, statistics.median(elapsed)))
