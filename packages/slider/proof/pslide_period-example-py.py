
from datetime import date, timedelta

from slider.pslide_period import pslide_period
from warp import Date

i = Date([date(2019, 1, 28) + timedelta(days=d) for d in range(6)])
result = pslide_period(
    [list(range(1, 7)), list(range(7, 13)), i],
    i,
    "month",
    lambda a, b, c: {"x": a, "y": b, "i": c},
)
print(result)
