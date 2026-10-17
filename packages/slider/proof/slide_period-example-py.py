
from datetime import date

from slider.slide_period import slide_period
from warp import Date

days = [date(2019, 1, 1), date(2019, 2, 1), date(2019, 4, 1), date(2019, 5, 1)]
i = Date(days)
result = slide_period([1, 2, 3, 4], i, "month", lambda w: w, before=1)
for index, piece in enumerate(result, start=1):
    print(f"[[{index}]]")
    print(piece)
    if index != len(result):
        print()
