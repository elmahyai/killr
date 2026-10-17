import sys

import numpy as np

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/statmod")
from statmod.canonic_digamma import canonic_digamma

mu = np.array([0.5, 1, 2], dtype=float)
print(canonic_digamma(mu))
