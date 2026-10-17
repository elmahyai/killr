import statistics
import time
import numpy as np
from quantreg.nlrq import (
    nlrq, nlrq_model, coef_nlrq, deviance_nlrq, tau_nlrq, fitted_nlrq, formula_nlrq,
    residuals_nlrq, predict_nlrq, logLik_nlrq, AIC_nlrq, extractAIC_nlrq, print_nlrq,
)
x = np.array([0.29999999999999999, 0.69999999999999996, 1.1000000000000001, 1.6000000000000001, 2, 2.3999999999999999, 2.8999999999999999, 3.2999999999999998, 3.7999999999999998, 4.2000000000000002, 4.7000000000000002, 5.0999999999999996, 5.5999999999999996, 6, 6.5, 7.0999999999999996, 7.5, 8, 8.5999999999999996, 9.0999999999999996])
y = np.array([2.650811306465664, 1.7567613456046705, 2.2011265905114694, 0.82802265962203714, 1.3414632594785239, 1.3792763085726993, 0.50600607458122593, 0.98764384225853341, 0.56119315324956009, 1.1748137129668095, -0.017468593015595779, 0.46949265250046485, 0.70214605230261262, 0.056141070632454881, 0.40699227108821601, -0.091686113719792489, 0.63109939258562864, 0.0020251565630449442, 0.37322919690115541, 0.053445614502425978])
D = {"x": x, "y": y}
fit = nlrq("y ~ a * exp(b * x)", D, {"a": 2.0, "b": -0.2}, tau=0.5, data_name="d")
def one():
    return [ord(ch) for ch in print_nlrq(fit).rstrip("\n")]

elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
value = one()
array = np.atleast_1d(np.asarray(value, dtype=float)).reshape(-1)
print(','.join(f'{item:.17g}' for item in array))
print(f'{statistics.median(elapsed):.17g}')
print(print_nlrq(fit), end="")
