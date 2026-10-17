"""Translation of CRAN quantreg 6.1.

The Barrodale-Roberts point estimate is the quantile regression linear
program, solved by SciPy HiGHS. The formula interface, sandwich standard
errors, and the Hill and Pickands tail exponents use that estimate.
Sparse Frisch-Newton, censored regression, and the total-variation smoother
still need SparseM, MatrixModels, and survival, which are not in the registry.
"""

from quantreg.anova import anova_rq, anova_rqlist, anova_rqs, print_anova_rq, rq_test_rank, summary_rqs
from quantreg.bandwidth import bandwidth_rq
from quantreg.boot import boot_rq, boot_rq_pxy, boot_rq_wxy, boot_rq_xy
from quantreg.combos import combos
from quantreg.constrained import rq_fit_fnc
from quantreg.crit import critval
from quantreg.dither import dither
from quantreg.fit import rq_fit, rq_fit_br, rq_wfit
from quantreg.infer import print_rq, print_rqs, print_summary_rq, print_summary_rqs, summary_rq
from quantreg.interior import (
    rq_fit_fnb,
    rq_fit_hogg,
    rq_fit_lasso,
    rq_fit_pfn,
    rq_fit_ppro,
    rq_fit_qfnb,
    rq_fit_scad,
)
from quantreg.likelihood import aic_rq, extract_aic_rq, log_lik_rq
from quantreg.messages import curv, nlrq_control, sfn_control, sfn_message
from quantreg.model import formula_rq, rq
from quantreg.more import (
    aic_rqs,
    akj,
    hill,
    hill_fit,
    lm_fit_recursive,
    log_lik_rqs,
    lasso_lambda_hat,
    lprq,
    pareto_test,
    pickands,
    pickands_fit,
    predict_rq,
    predict_rqs,
    print_hill,
    print_pickands,
    print_summary_hill,
    print_summary_pickands,
    summary_hill,
    summary_pickands,
)
from quantreg.orderstats import kselect, kunique, kuantile, q489
from quantreg.risk import qrisk, srisk

__all__ = [
    "aic_rq",
    "aic_rqs",
    "akj",
    "anova_rq",
    "anova_rqlist",
    "anova_rqs",
    "bandwidth_rq",
    "boot_rq",
    "boot_rq_pxy",
    "boot_rq_wxy",
    "boot_rq_xy",
    "combos",
    "critval",
    "curv",
    "dither",
    "extract_aic_rq",
    "formula_rq",
    "hill",
    "hill_fit",
    "kselect",
    "kunique",
    "kuantile",
    "lasso_lambda_hat",
    "lm_fit_recursive",
    "log_lik_rq",
    "log_lik_rqs",
    "lprq",
    "nlrq_control",
    "pareto_test",
    "pickands",
    "pickands_fit",
    "predict_rq",
    "predict_rqs",
    "print_anova_rq",
    "print_hill",
    "print_pickands",
    "print_rq",
    "print_rqs",
    "print_summary_hill",
    "print_summary_pickands",
    "print_summary_rq",
    "print_summary_rqs",
    "q489",
    "qrisk",
    "rq_test_rank",
    "rq",
    "rq_fit",
    "rq_fit_br",
    "rq_fit_fnb",
    "rq_fit_fnc",
    "rq_fit_hogg",
    "rq_fit_lasso",
    "rq_fit_pfn",
    "rq_fit_ppro",
    "rq_fit_qfnb",
    "rq_fit_scad",
    "rq_wfit",
    "sfn_control",
    "sfn_message",
    "srisk",
    "summary_hill",
    "summary_pickands",
    "summary_rq",
    "summary_rqs",
]
