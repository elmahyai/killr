.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(sys))
cat(exec_wait("false", std_out = FALSE, std_err = FALSE), "\n")
