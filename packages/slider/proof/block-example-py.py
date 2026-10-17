
from datetime import date, timedelta

from slider.block import block
from warp import Date

x = list(range(1, 7))
days = [date(2019, 1, 1) + timedelta(days=d) for d in (-2, -1, 0, 1, 2, 31)]
i = Date(days)


def _format_dates(piece: Date) -> str:
    base = date(1970, 1, 1)
    labels = []
    for offset in piece.days:
        if offset is None:
            labels.append("NA")
        else:
            labels.append(str(base + timedelta(days=int(offset))))
    return '[1] ' + " ".join(f'"{label}"' for label in labels)


result = block(i, i, period="year")
for index, piece in enumerate(result, start=1):
    print(f"[[{index}]]")
    print(_format_dates(piece))
    if index != len(result):
        print()
