"""Tests for normality, translated from nortest 1.0-4.

The five exports test the composite hypothesis that a sample is normal.
They call the normal cdf, the normal quantile, and the chi-square tail.
They do not import another translated package.
"""

from nortest.ad import ad_test
from nortest.cvm import cvm_test
from nortest.lillie import lillie_test
from nortest.pearson import pearson_test
from nortest.sf import sf_test

__all__ = [
    "ad_test",
    "cvm_test",
    "lillie_test",
    "pearson_test",
    "sf_test",
]
