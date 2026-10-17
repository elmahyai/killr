suppressPackageStartupMessages(library(quantreg))
tryCatch(table.rq(NULL), error=function(e) cat(conditionMessage(e), "\n"))
