"""Two-factor orthogonal rotation algorithm comparison plots."""

import numpy as np


def _trace(A, method, algorithm, maxit, kwargs):
    from .core import criterion

    A = np.asarray(A, dtype=float)
    k = A.shape[1]
    T = np.eye(k)
    previous_T = previous_G = None
    alpha = 1.0
    history = [T.copy()]
    f_history = [criterion(A @ T, method, kwargs).get("f")]
    for iteration in range(maxit + 1):
        q = criterion(A @ T, method, kwargs)
        G = A.T @ q["Gq"]
        M = T.T @ G
        Gp = G - T @ ((M + M.T) / 2)
        s = np.linalg.norm(Gp)
        if iteration >= maxit or s < 1e-5:
            break
        if algorithm in ("bb", "cayley") and previous_T is not None:
            dT, dG = T - previous_T, Gp - previous_G
            denominator = np.sum(dT * dG)
            alpha = np.clip(np.sum(dT * dT) / abs(denominator)
                            if denominator else alpha, 1e-10, 10.0)
        else:
            alpha *= 2.0
        target = max(f_history[max(0, len(f_history) - (1 if algorithm == "legacy" else 10)):])
        for _ in range(11):
            if algorithm == "cayley":
                W = Gp @ T.T - T @ Gp.T
                I = np.eye(k)
                candidate = np.linalg.solve(
                    I + alpha * W / 2, (I - alpha * W / 2) @ T)
            else:
                u, _, vt = np.linalg.svd(T - alpha * Gp, full_matrices=False)
                candidate = u @ vt
            f_candidate = criterion(A @ candidate, method, kwargs)["f"]
            if target - f_candidate > 0.5 * s * s * alpha:
                break
            alpha /= 2.0
        previous_T, previous_G, T = T, Gp, candidate
        history.append(T.copy())
        f_history.append(f_candidate)
    return {"T": history, "f": np.asarray(f_history), "iterations": len(history) - 1}


def plot2fOrthComparison(A, method="quartimax", items=None, nang=6000,
                         maxit=500, magnify=False, inset_pos="auto",
                         randomStart=False, **kwargs):
    """Plot legacy, BB, and Cayley paths for a two-factor orthogonal rotation.

    Returns the three algorithm results and the arrays used to draw each
    landscape.  The returned numeric data are useful for reproducible proofs.
    """
    import matplotlib.pyplot as plt
    from .core import criterion

    A = np.asarray(A, dtype=float)
    if A.ndim != 2 or A.shape[1] != 2:
        raise ValueError("A must be a two-factor loading matrix")
    if randomStart:
        from .core import Random_Start
        A = A @ Random_Start(2)
    results = {
        "legacy": _trace(A, method, "legacy", maxit, kwargs),
        "bb": _trace(A, method, "bb", maxit, kwargs),
        "cayley": _trace(A, method, "cayley", maxit, kwargs),
    }
    theta = np.linspace(0.0, 2 * np.pi, int(nang))
    landscape = np.asarray([
        criterion(A @ np.array([[np.cos(t), -np.sin(t)],
                                [np.sin(t), np.cos(t)]]), method, kwargs)["f"]
        for t in theta
    ])
    selected = np.arange(A.shape[0]) if items is None else np.asarray(items) - 1
    fig, axes = plt.subplots(2, 3, figsize=(12, 7), squeeze=False)
    labels = {"legacy": "Legacy, fwindow: 1",
              "bb": "Barzilai-Borwein, fwindow = 10",
              "cayley": "Cayley, fwindow = 10"}
    for column, (name, result) in enumerate(results.items()):
        path_theta = np.asarray([
            np.mod(np.arctan2(T[1, 0], T[0, 0]), 2 * np.pi)
            for T in result["T"]
        ])
        axes[0, column].plot(theta, landscape, color="0.55", linewidth=.8)
        axes[0, column].plot(path_theta, result["f"], "o-", color="steelblue",
                             markersize=3)
        axes[0, column].set(xlabel="theta (radians)", ylabel="f",
                            title=labels[name])
        axes[0, column].axhline(np.min(landscape), color="0.8",
                                linestyle="--")
        axes[1, column].add_patch(plt.Circle((0, 0), 1, fill=False,
                                             color="0.9"))
        axes[1, column].axhline(0, color="0.9", linestyle="--")
        axes[1, column].axvline(0, color="0.9", linestyle="--")
        for item in selected:
            coords = np.asarray([(A @ T)[item, :2] for T in result["T"]])
            axes[1, column].plot(coords[:, 0], coords[:, 1], linewidth=1)
            axes[1, column].plot(coords[[0, -1], 0], coords[[0, -1], 1],
                                 "ko", markersize=3)
        axes[1, column].set(xlim=(-1.1, 1.1), ylim=(-1.1, 1.1),
                            xlabel="Factor 1", ylabel="Factor 2")
    if magnify:
        # Keep the main figure deterministic; callers can inspect the returned
        # paths to choose an inset placement without changing numeric output.
        pass
    fig.suptitle("Rotation Landscapes and Migration Trajectories ("
                 + method.capitalize() + " Rotation)")
    fig.tight_layout()
    return {"legacy": results["legacy"], "bb": results["bb"],
            "cayley": results["cayley"], "theta": theta,
            "landscape": landscape, "figure": fig}
