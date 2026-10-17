import json
import statistics
import sys
import time

sys.path[:0] = ["/home/ahmed/killr_projects/killr/packages/stringdist"]
from stringdist.stringdist import stringdist

words = [
    "ca", "abc", "MARTHA", "MATHRA", "survey", "surgery",
    "leia", "leela", "crate", "trace", "dixon", "dicksonx",
    "john doe", "jane doe", "sock", "sck", "Euler", "Ellery",
    "Motörhead", "Motorhead", "abcabc", "aaa", "hello", "HeLl0",
    "DHCXXXXX", "HCDXXXXX", "RICK WARREN", "WARREN BUFFET",
    "", "a",
]


def one():
    extra = []
    for i in range(len(words) - 1):
        extra.extend(stringdist(words[i], words[i + 1], method="osa"))
        extra.extend(stringdist(words[i], words[i + 1], method="dl", weight=(0.5, 0.8, 0.3, 0.4)))
        extra.extend(stringdist(words[i], words[i + 1], method="jw", p=0.1))
        extra.extend(stringdist(words[i], words[i + 1], method="cosine", q=2))
    return (
        stringdist("ca", "abc")
        + stringdist("ca", "abc", method="dl")
        + stringdist("ABC", "abc")
        + stringdist("abc".lower(), "abc")
        + stringdist(["a", "b", "c", "d"], ["a", "c"])
        + stringdist("ab", "ba", weight=(1, 1, 1, 0.5))
        + stringdist("ca", "abc", weight=(0.5, 1, 1, 1))
        + stringdist("abc", "ca", weight=(0.5, 1, 1, 1))
        + stringdist("hello", "HeLl0", method="h")
        + stringdist("ab", "abc", method="hamming")
        + stringdist("ab", "ba", method="lcs")
        + stringdist("survey", "surgery", method="lcs")
        + stringdist("abc", "cba", method="qgram", q=1)
        + stringdist("abc", "cba", method="qgram", q=2)
        + stringdist("abcd", "abxd", method="qgram", q=2.9)
        + stringdist("aaa", "abc", method="cosine", q=1)
        + stringdist("abc", "abcabc", method="cosine", q=1)
        + stringdist("ab", "ab", method="cosine")
        + stringdist("", "a", method="cosine")
        + stringdist("aaa", "abc", method="jaccard", q=1)
        + stringdist("", "", method="jaccard")
        + stringdist("a", "b", method="jaccard", q=2)
        + stringdist("MARTHA", "MATHRA", method="jw")
        + stringdist("MARTHA", "MATHRA", method="jw", p=0.1)
        + stringdist("crate", "trace", method="jw", weight=(0.5, 1, 1))
        + stringdist("axiou", "aaeeiioouu", method="jw")
        + stringdist("john doe", "jane doe", method="jw", p=0.1, bt=0.8)
        + stringdist("Euler", "Gauss", method="soundex")
        + stringdist("Euler", "Ellery", method="soundex")
        + stringdist("sock", "sck", method="soundex")
        + stringdist("Motörhead", "Motorhead", method="dl")
        + stringdist("Motörhead", "Motorhead", method="dl", useBytes=True)
        + stringdist("Motörhead", "Motorhead", method="hamming", useBytes=True)
        + stringdist("Motörhead", "Motorhead", method="jw", useBytes=True)
        + stringdist("leia", "leela", method="lv", weight=(0.1, 1, 1))
        + stringdist("leia", "leela", method="dl", weight=(1, 0.1, 1, 1))
        + stringdist(["a", None, "b"], ["aa", "bb", "b"])
        + stringdist("", "")
        + stringdist("", "a")
        + extra
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
