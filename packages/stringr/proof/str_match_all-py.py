import json
import statistics
import time
from pathlib import Path

from stringi._na import NA, is_na
from stringr.match import str_match_all


def canon(value):
    if value is NA or value is None:
        return None
    if isinstance(value, dict):
        return {key: canon(item) for key, item in value.items()}
    if isinstance(value, list) and hasattr(value, "colnames"):
        names = value.colnames
        return {
            "colnames": None if names is None else list(names),
            "ncol": value.ncol,
            "rows": [[canon(cell) for cell in row] for row in value],
        }
    if isinstance(value, list):
        return [canon(item) for item in value]
    return value


def show(groups):
    blocks = []
    for index, matrix in enumerate(groups, start=1):
        lines = [f"[[{index}]]"]
        for row in matrix:
            lines.append(" ".join("NA" if is_na(cell) else cell for cell in row))
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks)


x = ["<a> <b>", "<a> <>", "<a>", "", NA]
out = Path("/home/ahmed/killr_projects/killr/packages/stringr/docs/output/str_match_all-python.txt")
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(show(str_match_all(x, "<(.*?)>")) + "\n", encoding="utf-8")


def one():
    strings = [
        " 219 733 8965",
        "329-293-8753 ",
        "banana",
        NA,
        "",
        "239 923 8115 and 842 566 4692",
    ] * 30
    phone = "([2-9][0-9]{2})[- .]([0-9]{3})[- .]([0-9]{4})"
    return {
        "phone": str_match_all(strings, phone),
        "named": str_match_all(
            ["219 733", NA, "", "no"],
            "(?<area>[2-9][0-9]{2})[- .](?<phone>[0-9]{3})",
        ),
        "tags": str_match_all(["<a> <b>", "<a> <>", "<a>", "", NA], "<(.*?)>"),
        "optional": str_match_all(["a"] * 5, "(a)(b)?"),
    }


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

print(json.dumps({"value": canon(value), "median_ms": statistics.median(elapsed)}, ensure_ascii=False))
