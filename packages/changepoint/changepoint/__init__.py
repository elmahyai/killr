"""Changepoint detection, translated from changepoint 2.3."""

from changepoint._api import (
    BINSEG,
    PELT,
    SEGNEIGH,
    ChangepointError,
    class_input,
    coef,
    cpt_mean,
    cpt_meanvar,
    cpt_reg,
    cpt_var,
    cpts,
    cpts_full,
    cpts_ts,
    cpttype,
    data_input,
    data_set,
    data_set_ts,
    decision,
    distribution,
    fitted,
    likelihood,
    logLik,
    method,
    minseglen,
    ncpts,
    ncpts_max,
    nseg,
    param,
    param_est,
    pen_type,
    pen_value,
    pen_value_full,
    penalty_decision,
    plot,
    residuals,
    seg_len,
    show,
    summary,
    test_stat,
    cpts_set,
    cpttype_set,
    data_set_set,
    distribution_set,
    test_stat_set,
    ncpts_max_set,
    param_est_set,
    pen_type_set,
    pen_value_set,
    method_set,
    cpts_full_set,
    minseglen_set,
    pen_value_full_set,
)
from changepoint._data import HC1, Lai2005fig3, Lai2005fig4, ftse100, wave_c44137

globals()["cpt.mean"] = cpt_mean
globals()["cpt.var"] = cpt_var
globals()["cpt.meanvar"] = cpt_meanvar
globals()["cpt.reg"] = cpt_reg
globals()["cpts<-"] = cpts_set
globals()["cpttype<-"] = cpttype_set
globals()["data.set<-"] = data_set_set
globals()["distribution<-"] = distribution_set
globals()["test.stat<-"] = test_stat_set
globals()["ncpts.max<-"] = ncpts_max_set
globals()["param.est<-"] = param_est_set
globals()["pen.type<-"] = pen_type_set
globals()["pen.value<-"] = pen_value_set
globals()["method<-"] = method_set
globals()["cpts.full<-"] = cpts_full_set
globals()["minseglen<-"] = minseglen_set
globals()["pen.value.full<-"] = pen_value_full_set
globals()["wave.c44137"] = wave_c44137

__all__ = [
    "BINSEG",
    "PELT",
    "SEGNEIGH",
    "class_input",
    "coef",
    "cpt_mean",
    "cpt_meanvar",
    "cpt_reg",
    "cpt_var",
    "cpts",
    "cpts_full",
    "cpts_ts",
    "cpttype",
    "data_input",
    "data_set",
    "data_set_ts",
    "decision",
    "distribution",
    "fitted",
    "likelihood",
    "logLik",
    "method",
    "minseglen",
    "ncpts",
    "ncpts_max",
    "nseg",
    "param",
    "param_est",
    "pen_type",
    "pen_value",
    "pen_value_full",
    "penalty_decision",
    "plot",
    "residuals",
    "seg_len",
    "show",
    "summary",
    "test_stat",
    "cpts_set",
    "cpttype_set",
    "data_set_set",
    "distribution_set",
    "test_stat_set",
    "ncpts_max_set",
    "param_est_set",
    "pen_type_set",
    "pen_value_set",
    "method_set",
    "cpts_full_set",
    "minseglen_set",
    "pen_value_full_set",
    "ftse100",
    "HC1",
    "Lai2005fig3",
    "Lai2005fig4",
    "wave_c44137",
]
