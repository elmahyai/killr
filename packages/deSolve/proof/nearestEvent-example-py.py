import sys

import numpy as np

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/deSolve")
from deSolve.nearestEvent import nearestEvent

events = np.sort(
    np.array(
        [
            0,
            2,
            3,
            4 + 1e-10,
            5,
            7 - 1e-10,
            7 + 6e-15,
            7.5,
            9,
            24.9999,
            25,
            80,
            1001,
            1e300,
        ],
        dtype=float,
    )
)
times = np.sort(
    np.array(
        [
            0,
            *range(1, 8),
            4.5,
            6.75,
            7.5,
            9.2,
            9.0001,
            25,
            879,
            1e3,
            1e300 + 5,
        ],
        dtype=float,
    )
)
nearest = nearestEvent(times, events)
print("       times      nearest")
for time, event in zip(times, nearest, strict=True):
    print(f"{time:12.4e} {event:12.4e}")
