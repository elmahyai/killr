.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(sys))
tryCatch(eval_fork(1), error = function(e) cat(conditionMessage(e), "\n"))
