"""Nelder-Mead as R's optim implements it in nmmin."""

import math


def nelder_mead(start, fn, maxit=500, abstol=float("-inf"), reltol=None, alpha=1.0, beta=0.5, gamma=2.0):
    """Minimize fn. Returns par, value, function count, and the convergence code."""
    if reltol is None:
        reltol = math.sqrt(2.220446049250313e-16)
    n = len(start)
    point = [float(value) for value in start]
    big = 1.0e35
    if maxit <= 0:
        return {"par": point, "value": float(fn(point)), "counts": 0, "convergence": 0}
    value = float(fn(point))
    if not math.isfinite(value):
        raise ValueError("function cannot be evaluated at initial parameters")
    # P has n+1 rows (coordinates plus the function value) and n+2 columns.
    columns = n + 2
    rows = n + 1
    simplex = [[0.0 for _ in range(columns)] for _ in range(rows)]
    funcount = 1
    convtol = reltol * (abs(value) + reltol)
    n1 = n + 1
    centroid_column = n + 1
    simplex[n][0] = value
    for i in range(n):
        simplex[i][0] = point[i]
    low = 1
    step = 0.0
    for i in range(n):
        candidate = 0.1 * abs(point[i])
        if candidate > step:
            step = candidate
    if step == 0.0:
        step = 0.1
    size = 0.0
    for j in range(2, n1 + 1):
        for i in range(n):
            simplex[i][j - 1] = point[i]
        trystep = step
        while simplex[j - 2][j - 1] == point[j - 2]:
            simplex[j - 2][j - 1] = point[j - 2] + trystep
            trystep *= 10
        size += trystep
    oldsize = size
    calcvert = True
    fail = 0
    while True:
        if calcvert:
            for j in range(n1):
                if j + 1 != low:
                    for i in range(n):
                        point[i] = simplex[i][j]
                    try:
                        value = float(fn(point))
                    except Exception:
                        value = big
                    if not math.isfinite(value):
                        value = big
                    funcount += 1
                    simplex[n][j] = value
            calcvert = False
        low_value = simplex[n][low - 1]
        high_value = low_value
        high = low
        for j in range(1, n1 + 1):
            if j != low:
                value = simplex[n][j - 1]
                if value < low_value:
                    low = j
                    low_value = value
                if value > high_value:
                    high = j
                    high_value = value
        if high_value <= low_value + convtol or low_value <= abstol:
            break
        for i in range(n):
            total = -simplex[i][high - 1]
            for j in range(n1):
                total += simplex[i][j]
            simplex[i][centroid_column] = total / n
        for i in range(n):
            point[i] = (1.0 + alpha) * simplex[i][centroid_column] - alpha * simplex[i][high - 1]
        try:
            value = float(fn(point))
        except Exception:
            value = big
        if not math.isfinite(value):
            value = big
        funcount += 1
        reflected = value
        if reflected < low_value:
            simplex[n][centroid_column] = value
            for i in range(n):
                expanded = gamma * point[i] + (1 - gamma) * simplex[i][centroid_column]
                simplex[i][centroid_column] = point[i]
                point[i] = expanded
            try:
                value = float(fn(point))
            except Exception:
                value = big
            if not math.isfinite(value):
                value = big
            funcount += 1
            if value < reflected:
                for i in range(n):
                    simplex[i][high - 1] = point[i]
                simplex[n][high - 1] = value
            else:
                for i in range(n):
                    simplex[i][high - 1] = simplex[i][centroid_column]
                simplex[n][high - 1] = reflected
        else:
            if reflected < high_value:
                for i in range(n):
                    simplex[i][high - 1] = point[i]
                simplex[n][high - 1] = reflected
            for i in range(n):
                point[i] = (1 - beta) * simplex[i][high - 1] + beta * simplex[i][centroid_column]
            try:
                value = float(fn(point))
            except Exception:
                value = big
            if not math.isfinite(value):
                value = big
            funcount += 1
            if value < simplex[n][high - 1]:
                for i in range(n):
                    simplex[i][high - 1] = point[i]
                simplex[n][high - 1] = value
            elif reflected >= high_value:
                calcvert = True
                size = 0.0
                for j in range(n1):
                    if j + 1 != low:
                        for i in range(n):
                            simplex[i][j] = beta * (simplex[i][j] - simplex[i][low - 1]) + simplex[i][low - 1]
                            size += abs(simplex[i][j] - simplex[i][low - 1])
                if size < oldsize:
                    oldsize = size
                else:
                    fail = 10
                    break
        if funcount > maxit:
            break
    result = [simplex[i][low - 1] for i in range(n)]
    if funcount > maxit:
        fail = 1
    return {
        "par": result,
        "value": simplex[n][low - 1],
        "counts": funcount,
        "convergence": fail,
    }
