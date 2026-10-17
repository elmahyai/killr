import statistics
import sys
import time

sys.path[:0] = ["/home/ahmed/killr_projects/killr/packages/stringdist"]
from stringdist.stringsim import stringsim

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
        extra.extend(stringsim(words[i], words[i + 1], method="osa"))
        extra.extend(
            stringsim(
                words[i],
                words[i + 1],
                method="dl",
                weight=(0.5, 0.8, 0.3, 0.4),
            )
        )
        extra.extend(stringsim(words[i], words[i + 1], method="jw", p=0.1))
        extra.extend(stringsim(words[i], words[i + 1], method="cosine", q=2))
    return (
        stringsim("ca", "abc")
        + stringsim("ca", "abc", method="dl")
        + stringsim("ABC", "abc")
        + stringsim("abc".lower(), "abc")
        + stringsim(["a", "b", "c", "d"], ["a", "c"])
        + stringsim("ab", "ba", weight=(1, 1, 1, 0.5))
        + stringsim("ca", "abc", weight=(0.5, 1, 1, 1))
        + stringsim("abc", "ca", weight=(0.5, 1, 1, 1))
        + stringsim("hello", "HeLl0", method="h")
        + stringsim("ab", "abc", method="hamming")
        + stringsim("ab", "ba", method="lcs")
        + stringsim("survey", "surgery", method="lcs")
        + stringsim("abc", "cba", method="qgram", q=1)
        + stringsim("abc", "cba", method="qgram", q=2)
        + stringsim("abcd", "abxd", method="qgram", q=2.9)
        + stringsim("aaa", "abc", method="cosine", q=1)
        + stringsim("abc", "abcabc", method="cosine", q=1)
        + stringsim("ab", "ab", method="cosine")
        + stringsim("", "a", method="cosine")
        + stringsim("aaa", "abc", method="jaccard", q=1)
        + stringsim("", "", method="jaccard")
        + stringsim("a", "b", method="jaccard", q=2)
        + stringsim("MARTHA", "MATHRA", method="jw")
        + stringsim("MARTHA", "MATHRA", method="jw", p=0.1)
        + stringsim("crate", "trace", method="jw", weight=(0.5, 1, 1))
        + stringsim("axiou", "aaeeiioouu", method="jw")
        + stringsim("john doe", "jane doe", method="jw", p=0.1, bt=0.8)
        + stringsim("Euler", "Gauss", method="soundex")
        + stringsim("Euler", "Ellery", method="soundex")
        + stringsim("sock", "sck", method="soundex")
        + stringsim("Motörhead", "Motorhead", method="dl")
        + stringsim("Motörhead", "Motorhead", method="dl", useBytes=True)
        + stringsim("Motörhead", "Motorhead", method="hamming", useBytes=True)
        + stringsim("Motörhead", "Motorhead", method="jw", useBytes=True)
        + stringsim("leia", "leela", method="lv", weight=(0.1, 1, 1))
        + stringsim("leia", "leela", method="dl", weight=(1, 0.1, 1, 1))
        + stringsim(["a", None, "b"], ["aa", "bb", "b"])
        + stringsim("", "")
        + stringsim("", "a")
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
