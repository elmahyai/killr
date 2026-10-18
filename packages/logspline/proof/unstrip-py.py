from _batch_common import run, unstrip
import numpy as np
run("unstrip", lambda x: unstrip(x), np.arange(6).reshape(2, 3))
