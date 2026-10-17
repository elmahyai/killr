import statistics
import time

from mass.polr import polr, polr_compare_vector


def _col(text: str) -> list[str]:
    return text.split("|")


_HOUSING = {
    "Sat": _col(
        "Low|Medium|High|Low|Medium|High|Low|Medium|High|Low|Medium|High|Low|Medium|High|Low|Medium|High|Low|Medium|High|Low|Medium|High|Low|Medium|High|Low|Medium|High|Low|Medium|High|Low|Medium|High|Low|Medium|High|Low|Medium|High|Low|Medium|High|Low|Medium|High|Low|Medium|High|Low|Medium|High|Low|Medium|High|Low|Medium|High|Low|Medium|High|Low|Medium|High|Low|Medium|High|Low|Medium|High"
    ),
    "Infl": _col(
        "Low|Low|Low|Medium|Medium|Medium|High|High|High|Low|Low|Low|Medium|Medium|Medium|High|High|High|Low|Low|Low|Medium|Medium|Medium|High|High|High|Low|Low|Low|Medium|Medium|Medium|High|High|High|Low|Low|Low|Medium|Medium|Medium|High|High|High|Low|Low|Low|Medium|Medium|Medium|High|High|High|Low|Low|Low|Medium|Medium|Medium|High|High|High|Low|Low|Low|Medium|Medium|Medium|High|High|High"
    ),
    "Type": _col(
        "Tower|Tower|Tower|Tower|Tower|Tower|Tower|Tower|Tower|Apartment|Apartment|Apartment|Apartment|Apartment|Apartment|Apartment|Apartment|Apartment|Atrium|Atrium|Atrium|Atrium|Atrium|Atrium|Atrium|Atrium|Atrium|Terrace|Terrace|Terrace|Terrace|Terrace|Terrace|Terrace|Terrace|Terrace|Tower|Tower|Tower|Tower|Tower|Tower|Tower|Tower|Tower|Apartment|Apartment|Apartment|Apartment|Apartment|Apartment|Apartment|Apartment|Apartment|Atrium|Atrium|Atrium|Atrium|Atrium|Atrium|Atrium|Atrium|Atrium|Terrace|Terrace|Terrace|Terrace|Terrace|Terrace|Terrace|Terrace|Terrace"
    ),
    "Cont": _col(
        "Low|Low|Low|Low|Low|Low|Low|Low|Low|Low|Low|Low|Low|Low|Low|Low|Low|Low|Low|Low|Low|Low|Low|Low|Low|Low|Low|Low|Low|Low|Low|Low|Low|Low|Low|Low|High|High|High|High|High|High|High|High|High|High|High|High|High|High|High|High|High|High|High|High|High|High|High|High|High|High|High|High|High|High|High|High|High|High|High|High"
    ),
    "Freq": [
        int(x)
        for x in "21|21|28|34|22|36|10|11|36|61|23|17|43|35|40|26|18|54|13|9|10|8|8|12|6|7|9|18|6|7|15|13|13|7|5|11|14|19|37|17|23|40|3|5|23|78|46|43|48|45|86|15|25|62|20|23|20|10|22|24|7|10|21|57|23|13|31|21|13|5|6|13".split(
            "|"
        )
    ],
}


def one():
    fit = polr(
        "Sat ~ Infl + Type + Cont",
        _HOUSING,
        weights=_HOUSING["Freq"],
        model=False,
        response_levels=["Low", "Medium", "High"],
        predictor_levels={
            "Infl": ["Low", "Medium", "High"],
            "Type": ["Tower", "Apartment", "Atrium", "Terrace"],
            "Cont": ["Low", "High"],
        },
    )
    return polr_compare_vector(fit)


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
for item in value:
    print("%.17g" % float(item))
print("%.17g" % statistics.median(elapsed))
