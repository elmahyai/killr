"""Python translation of the R package rpart."""

from rpart.control import rpart_control
from rpart.fit import (
    meanvar,
    na_rpart,
    path_rpart,
    plotcp,
    post,
    printcp,
    prune,
    prune_rpart,
    rpart,
    rpart_exp,
    rsq_rpart,
    snip_rpart,
    xpred_rpart,
)

globals()["na.rpart"] = na_rpart
globals()["path.rpart"] = path_rpart
globals()["prune.rpart"] = prune_rpart
globals()["rsq.rpart"] = rsq_rpart
globals()["snip.rpart"] = snip_rpart
globals()["xpred.rpart"] = xpred_rpart
globals()["rpart.exp"] = rpart_exp
globals()["rpart.control"] = rpart_control

__all__ = [
    "rpart",
    "rpart_control",
    "rpart.control",
    "meanvar",
    "na_rpart",
    "na.rpart",
    "path_rpart",
    "path.rpart",
    "plotcp",
    "post",
    "printcp",
    "prune",
    "prune_rpart",
    "prune.rpart",
    "rsq_rpart",
    "rsq.rpart",
    "snip_rpart",
    "snip.rpart",
    "xpred_rpart",
    "xpred.rpart",
    "rpart_exp",
    "rpart.exp",
]
