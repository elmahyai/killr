import math
import statistics
import time


def _fc(value):
    if value is None:
        return "NULL"
    if isinstance(value, float) and math.isnan(value):
        return "NA"
    if isinstance(value, bool):
        return "T" if value else "F"
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        if value and isinstance(value[0], dict):
            return "\3".join(
                f"{row['components']},{'T' if row['extensible'] else 'F'}" for row in value
            )
        if value and isinstance(value[0], str):
            return "\1".join(value)
        return "\2".join(_fc(item) for item in value)
    return "?"


def summarize(result):
    keys = [
        "is_empty",
        "is_canonical",
        "bad_components",
        "is_standardizable",
        "is_verified",
        "standardization",
        "components",
        "expansions",
        "extensions",
        "pointers",
        "is_FOSS",
        "restricts_use",
    ]
    return "|".join(_fc(result[key]) for key in keys)


def one():
    from tools.license import analyze_license

    specs = [
        "GPL-2",
        "LGPL (>= 2.0, < 3) | Mozilla Public License",
        "GPL-2 | file LICENCE",
        "GPL (>= 2) | BSD_3_clause + file LICENSE",
        "Artistic-2.0 | AGPL-3 + file LICENSE",
    ]
    return "\n".join(summarize(analyze_license(spec)) for spec in specs) + "\n"


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(value, end="")
print("MS")
print(f"{statistics.median(elapsed):.17g}")
