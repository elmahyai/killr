.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(sys))
tryCatch(eval_safe(1), error = function(e) cat(conditionMessage(e), "\n"))
