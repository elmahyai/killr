import statistics
import time

from survival.untangle_specials import untangle_specials


def serialize_untangle(u):
    vars_part = "|".join(u["vars"])
    terms_part = " ".join(str(value) for value in u["terms"])
    tvar = u.get("tvar")
    if tvar is None:
        tvar_part = ""
    elif isinstance(tvar, list):
        tvar_part = " ".join(str(value) for value in tvar)
    else:
        tvar_part = str(tvar)
    return [vars_part, terms_part, tvar_part]


def _help_example_terms():
    return {
        "specials": {"strata": [4]},
        "factors": {
            "matrix": [
                [0, 0, 0, 0],
                [1, 0, 0, 0],
                [0, 1, 0, 1],
                [0, 0, 1, 1],
            ],
            "rownames": ["Surv(tt, ss)", "x", "z", "strata(id)"],
            "colnames": ["x", "z", "strata(id)", "z:strata(id)"],
        },
        "order": [1, 1, 1, 2],
        "response": 1,
    }


def _two_strata_terms():
    return {
        "specials": {"strata": [2, 3]},
        "factors": {
            "matrix": [
                [0, 0],
                [1, 0],
                [0, 1],
            ],
            "rownames": ["Surv(tt, ss)", "strata(a)", "strata(b)"],
            "colnames": ["strata(a)", "strata(b)"],
        },
        "order": [1, 1],
        "response": 1,
    }


def one():
    tms = _help_example_terms()
    u1 = untangle_specials(tms, "strata")
    u2 = untangle_specials(tms, "strata", order=[1, 2])
    u3 = untangle_specials(tms, "tt")
    u4 = untangle_specials(_two_strata_terms(), "strata")
    out = []
    for item in (u1, u2, u3, u4):
        out.extend(serialize_untangle(item))
    return out


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print("\n".join(value))
print("MS")
print(f"{statistics.median(elapsed):.17g}")
