.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(sys))
out <- exec_internal("printf", c("%s", "hello")); cat(out$status, " ", rawToChar(out$stdout), "\n", sep = "")
