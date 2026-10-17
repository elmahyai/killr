import json
import statistics
import sys
import time

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/lattice")
from lattice.core import xyplot
from lattice.current_column import current_column
from lattice.lattice_status import lattice_get_status, lattice_set_status, record_printed_trellis
from lattice.packet_panel_default import packet_panel_default


def _default_panel_layout(npanels: int) -> list[int]:
    """Match ``print.trellis`` when ``compute.layout`` yields ``c(0, npanels, 1)``."""
    device_aspect = 1.0
    panel_aspect = 1.0
    plots_per_page = npanels
    m = max(1, round((plots_per_page * device_aspect / panel_aspect) ** 0.5))
    n = -(-plots_per_page // m)
    m = -(-plots_per_page // n)
    return [n, m, 1]


def _collect_current_columns(layout, condlevels, *, prefix, skip):
    ncol, nrow = int(layout[0]), int(layout[1])
    collected = []
    for row in range(1, nrow + 1):
        for column in range(1, ncol + 1):
            if packet_panel_default(layout, condlevels, 1, row, column, skip) is None:
                continue
            lattice_set_status(
                prefix=prefix,
                **{"current.focus.row": row, "current.focus.column": column},
            )
            collected.append(float(current_column(prefix=prefix)))
    return collected


def one():
    mpg = [
        21,
        21,
        22.8,
        21.4,
        18.7,
        18.1,
        14.3,
        24.4,
        22.8,
        19.2,
        17.8,
        16.4,
        17.3,
        15.2,
        10.4,
        10.4,
        14.7,
        32.4,
        30.4,
        33.9,
        21.5,
        15.5,
        15.2,
        13.3,
        19.2,
        27.3,
        26,
        30.4,
        15.8,
        19.7,
        15,
        21.4,
    ]
    wt = [
        2.62,
        2.875,
        2.32,
        3.215,
        3.44,
        3.46,
        3.57,
        3.19,
        3.15,
        3.44,
        3.44,
        4.07,
        3.73,
        3.78,
        5.25,
        5.424,
        5.345,
        2.2,
        1.615,
        1.835,
        2.465,
        3.52,
        3.435,
        3.84,
        3.845,
        1.935,
        2.14,
        1.513,
        3.17,
        2.77,
        3.57,
        2.78,
    ]
    cyl = [6, 6, 4, 6, 8, 6, 8, 4, 4, 6, 6, 8, 8, 8, 8, 8, 8, 4, 4, 4, 4, 8, 8, 8, 8, 4, 4, 4, 8, 6, 8, 4]
    plot = xyplot("mpg ~ wt | cyl", {"mpg": mpg, "wt": wt, "cyl": cyl})
    record_printed_trellis(plot)
    prefix = lattice_get_status("current.prefix")
    layout = _default_panel_layout(3)
    return _collect_current_columns(layout, [[1, 2, 3]], prefix=prefix, skip=[False])


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": [statistics.median(elapsed)]}))
