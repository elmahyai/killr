from ordinal.slice import slice
"""Python translation of the R package ordinal. The model functions are still open."""

from ordinal.control import clm2_control, clm_control, clmm2_control, clmm_control
from ordinal.links import (
    dgumbel,
    dlgamma,
    gcauchy,
    ggumbel,
    glgamma,
    glogis,
    gnorm,
    pgumbel,
    plgamma,
    qgumbel,
)

__all__ = [
    "convergence",
    "drop_coef",
    "slice",
    "clm2_control",
    "clm_control",
    "clmm2_control",
    "clmm_control",
    "dgumbel",
    "dlgamma",
    "gcauchy",
    "ggumbel",
    "glgamma",
    "glogis",
    "gnorm",
    "pgumbel",
    "plgamma",
    "qgumbel",
    "nominal_test",
    "rgumbel",
    "cond_var",
    "scale_test",
]
from ordinal.drop_coef import drop_coef
from ordinal.convergence import convergence
from ordinal.nominal_test import nominal_test
from ordinal.rgumbel import rgumbel
from ordinal.cond_var import cond_var
from ordinal.scale_test import scale_test
