# Singular covariance gives a missing loglik

R's `mvn` wrappers report a singular covariance as `loglik = NA` with a return code of -1. `mvnXXX` does this in the Python port too: it returns NaN with `returnCode` -1.

`mvnXII` and `mvnXXI` differ. R sets the loglik to NA only when it is above `signif(.Machine$double.xmax, 6)`, which is 1.79769e308. The Python ports return `inf` with `returnCode` 0 for a zero-variance cluster, for example a single point. A caller that tests for NA will then take the value as a real loglik.

Callers that sum or compare loglik values across clusters must map that case to NaN. `mclust/plot_hc.py` does this in `_mvn_loglik`, for `cloglik.hc`. The `mvnXII` and `mvnXXI` ports themselves are not changed here.
