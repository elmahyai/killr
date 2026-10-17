"""Empirical fluctuation processes for each VAR equation.

The process itself is strucchange::efp. This function only builds the
per-equation regression that efp receives.
"""


class _Equation:
    """The ``x`` and ``y`` pair ``strucchange.efp`` accepts in place of a formula."""

    def __init__(self, x, y):
        self.x = x
        self.y = y


def stability(x, type="OLS-CUSUM", h=0.15, dynamic=False, rescale=True):
    from strucchange import efp

    processes = {}
    design = x.datamat[:, x.K:]
    response = x.datamat[:, :x.K]
    for index, name in enumerate(x.names):
        processes[name] = efp(
            _Equation(design, response[:, index]),
            type=type, h=h, dynamic=dynamic, rescale=rescale,
        )
    return {"stability": processes, "names": list(x.names), "K": x.K}
