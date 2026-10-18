from _batch_common import FIT, run, rpqlsd
import numpy as np
run("rpqlsd", lambda x: rpqlsd(
    np.r_[FIT["coef.pol"], FIT["coef.kts"]], FIT["knots"], FIT["bound"],
    0, x), [0.1, 0.5, 0.9])
