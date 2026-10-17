import pathlib
import sys
import time
import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).parents[1]))
from mitools import MIcombine, MIextract, imputationList, withPV


def cases():
    datasets = [np.array([[1., 2.], [3., 4.]]), np.array([[2., 3.], [4., 5.]])]
    il = imputationList(datasets)
    combined = MIcombine([np.array([1., 2.]), np.array([1.2, 2.4]), np.array([.8, 1.6])],
                         [np.diag([.25, .36])] * 3)
    extracted = MIextract([{"x": 1}, {"x": 2}, {"x": 3}], expr="x")
    data = {"PV1": np.array([1., 2.]), "PV2": np.array([2., 3.]),
            "z": np.array([10., 20.])}
    pv = withPV({"x": ["PV1", "PV2"]}, data, lambda d: float(np.mean(d["x"])))
    return {
        "imputationList": np.array([len(il)], dtype=float),
        "MIcombine": np.r_[combined.coefficients, combined.variance.ravel()],
        "MIextract": np.asarray(extracted, dtype=float),
        "withPV": np.asarray(pv, dtype=float),
    }


def main():
    for name, function in cases().items():
        value = function
        times = []
        for _ in range(20):
            start = time.perf_counter()
            current = cases()[name]
            times.append((time.perf_counter() - start) * 1000)
        print(f"{name}|{' '.join(f'{x:.12g}' for x in value)}|{np.median(times):.9f}")


if __name__ == "__main__":
    main()
