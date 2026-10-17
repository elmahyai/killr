"""vec2var, from a Johansen result."""

import numpy as np

from urca.johansen import CaJo


def vec2var(z, r=1):
    if not isinstance(z, CaJo):
        raise TypeError("provide an object from ca_jo")
    r = int(r)
    p_vars = z.x.shape[1]
    if not (1 <= r < p_vars):
        raise ValueError(f"cointegration rank r must be in 1 to {p_vars - 1}")
    etc = z.ZK @ z.V[:, :r]
    design = np.column_stack([etc, z.Z1])
    coef, _resid, _rank, _sv = np.linalg.lstsq(design, z.Z0, rcond=None)
    row_names = [f"etc{i}" for i in range(1, r + 1)] + list(z.z1_names)
    pi = z.W[:, :r] @ z.V[:, :r].T
    names = list(z.colnames)
    if z.ecdet == "const":
        det = pi[:, z.P].reshape(1, -1)
        det_names = ["constant"]
        pi = np.delete(pi, z.P, axis=1)
    elif z.ecdet == "none":
        det = coef[row_names.index("constant")].reshape(1, -1)
        det_names = ["constant"]
    else:
        trend_name = z.zk_names[z.P]
        det = np.vstack([coef[row_names.index("constant")], pi[:, z.P]])
        det_names = ["constant", trend_name]
        pi = np.delete(pi, z.P, axis=1)
    if z.season is not None:
        season_names = [f"sd{i}" for i in range(1, int(z.season))]
        det = np.vstack([det, coef[[row_names.index(name) for name in season_names]]])
        det_names = det_names + season_names
    skip = set(det_names) | {f"etc{i}" for i in range(1, r + 1)}
    keep = [i for i, name in enumerate(row_names) if name not in skip]
    gamma = coef[keep].T
    lag = int(z.lag)
    blocks = []
    if z.spec == "transitory":
        if lag == 2:
            blocks = [gamma + pi + np.eye(p_vars), -gamma]
        else:
            blocks = _split_gamma(gamma, pi, p_vars, lag, longrun=False)
    else:
        if lag == 2:
            first = gamma + np.eye(p_vars)
            blocks = [first, pi + np.eye(p_vars) - first]
        else:
            blocks = _split_gamma(gamma, pi, p_vars, lag, longrun=True)
    level = _embed_levels(z.x, lag + 1)
    det_columns = _det_columns(z, det_names)
    datamat = np.column_stack([level[:, :p_vars], det_columns, level[:, p_vars:]])
    cursor = p_vars + len(det_names)
    rebuilt = datamat[:, :p_vars] - datamat[:, p_vars:cursor] @ det
    for block in blocks:
        width = block.shape[1]
        rebuilt = rebuilt - datamat[:, cursor:cursor + width] @ block.T
        cursor += width
    return {
        "deterministic": det.T,
        "A": blocks,
        "p": lag,
        "K": p_vars,
        "y": z.x,
        "obs": z.Z0.shape[0],
        "datamat": datamat,
        "resid": rebuilt,
        "r": r,
        "names": names,
    }


def _split_gamma(gamma, pi, p_vars, lag, longrun):
    ends = list(range(p_vars - 1, p_vars * (lag - 1), p_vars))
    starts = [end - p_vars + 1 for end in ends]
    if longrun:
        first = gamma[:, starts[0]:ends[0] + 1] + np.eye(p_vars)
    else:
        first = gamma[:, starts[0]:ends[0] + 1] + pi + np.eye(p_vars)
    blocks = [first]
    for i in range(1, lag - 1):
        current = gamma[:, starts[i]:ends[i] + 1]
        previous = gamma[:, starts[i - 1]:ends[i - 1] + 1]
        blocks.append(current - previous)
    last_g = gamma[:, starts[-1]:ends[-1] + 1]
    if longrun:
        blocks.append(pi - last_g)
    else:
        blocks.append(-last_g)
    return blocks


def _embed_levels(x, dimension):
    rows = x.shape[0] - dimension + 1
    width = x.shape[1]
    out = np.empty((rows, dimension * width))
    for lag in range(dimension):
        out[:, lag * width:(lag + 1) * width] = x[(dimension - 1 - lag):(x.shape[0] - lag)]
    return out


def _det_columns(z, det_names):
    # rhs in R is built from a constant and, for a trend, the trend column of ZK plus Z1 without its constant.
    if z.ecdet == "const":
        columns = np.ones((z.Z0.shape[0], 1))
        names = ["constant"]
    elif z.ecdet == "trend":
        columns = np.column_stack([np.ones(z.Z0.shape[0]), z.ZK[:, z.P], z.Z1[:, 1:]])
        names = ["constant", z.zk_names[z.P], *z.z1_names[1:]]
    else:
        columns = z.Z1
        names = list(z.z1_names)
    index = [names.index(name) for name in det_names]
    return columns[:, index]
