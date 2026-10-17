"""Information criteria shared by aic, cp, and gcv."""

from ._common import dp_values, n_observations


def aic(x, *args, pen: float = 2, **kwargs):
    lk, df1, df2 = dp_values(x)
    return {"lik": lk, "infl": df1, "vari": df2, "aic": -2.0 * lk + pen * df1}


def cp(x, *args, sig2: float = 1, **kwargs):
    lk, df1, df2 = dp_values(x)
    n = n_observations(x)
    return {"lik": lk, "infl": df1, "vari": df2, "n": n,
            "cp": (-2.0 * lk) / sig2 - n + 2.0 * df1}


def gcv(x, *args, **kwargs):
    lk, df1, df2 = dp_values(x)
    n = n_observations(x)
    return {"lik": lk, "infl": df1, "vari": df2,
            "gcv": (-2.0 * n * lk) / (n - df1) ** 2}

