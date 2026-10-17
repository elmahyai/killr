"""Pooled residual standard deviation from ``lmList`` fits (nlme ``pooledSD``)."""

from __future__ import annotations

import math
from dataclasses import dataclass

from nlme.lmlistformula import LmFit, LmList


@dataclass(slots=True)
class PooledSD:
    """Scalar pooled standard deviation with residual ``df`` like R's attribute."""

    value: float
    df: float

    def __float__(self) -> float:
        return self.value


def pooledSD(object) -> PooledSD:
    """Pool residual standard deviations across non-null ``lmList`` elements."""
    if not isinstance(object, LmList):
        raise TypeError('object must inherit from class "lmList"')
    rss_sum = 0.0
    df_sum = 0.0
    for _name, element in object.entries:
        if element is None or isinstance(element, BaseException):
            continue
        if not isinstance(element, LmFit):
            raise TypeError("lmList entries must be lm fits")
        rss_sum += element.rss
        df_sum += element.n_resid - len(element.coefficients)
    if df_sum == 0:
        raise ValueError("no degrees of freedom for estimating std. dev.")
    return PooledSD(value=math.sqrt(rss_sum / df_sum), df=float(df_sum))
