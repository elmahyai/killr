.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(sys))
out <- r_internal(c("--vanilla", "-q", "--slave", "-e", "cat(6*7)")); cat(rawToChar(out$stdout), "\n", sep = "")
