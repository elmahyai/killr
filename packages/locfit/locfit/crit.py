"""Critical-value object used by locfit simultaneous-band helpers.

For a one-dimensional constant (``const = (0, 1)``, ``d = 1``) and no
residual degrees of freedom (``rdf = 0``), R's ``scritval`` returns the
two-sided Gaussian quantile, ``qnorm((1 + cov) / 2)``. That case is computed
here exactly with the standard library.

For ``d >= 1`` other than that case, and ``rdf = 0``, the ``scritval`` routine
of the locfit C kernel is ported in ``crates/locfit`` (``critval.rs``) and
called through the crate's ``scritval`` binding (for ``kappa0``, ``d = 1``
gives a ``const`` of length 2). Other cases (``rdf > 0``) raise
``NotImplementedError`` instead of returning an approximation.
"""

from dataclasses import dataclass
from statistics import NormalDist


@dataclass
class Kappa:
    const: object
    d: int
    cov: float
    rdf: float = 0.0
    crit_val: float = 0.0


def crit(fit=None, const=(0.0, 1.0), d=1, cov=0.95, rdf=0.0):
    if fit is not None and hasattr(fit, "critval"):
        z = fit.critval
        if const == (0.0, 1.0) and d == 1 and cov == 0.95 and rdf == 0:
            return z
        const = getattr(z, "const", const)
        d = getattr(z, "d", d)
        cov = getattr(z, "cov", cov)
        rdf = getattr(z, "rdf", rdf)
    if tuple(const) == (0.0, 1.0) and int(d) == 1 and float(rdf) == 0.0:
        cov = float(cov)
        if not 0.0 < cov < 1.0:
            raise ValueError("cov must lie strictly between 0 and 1")
        z = NormalDist().inv_cdf((1.0 + cov) / 2.0)
        return Kappa(tuple(const), int(d), cov, float(rdf), z)
    if int(d) >= 1 and float(rdf) == 0.0:
        # Imported here so the translated package does not need the crate
        # unless a critical value is requested.
        import locfit as crate  # crates/locfit, the loaded C kernel

        cov = float(cov)
        if not 0.0 < cov < 1.0:
            raise ValueError("cov must lie strictly between 0 and 1")
        k0 = [float(v) for v in const]
        z = crate.scritval(k0, int(d), cov)
        return Kappa(tuple(const), int(d), cov, float(rdf), z)
    raise NotImplementedError(
        "crit: only rdf = 0 is translated. The t-process (rdf > 0) is not in "
        "crates/locfit yet.")
