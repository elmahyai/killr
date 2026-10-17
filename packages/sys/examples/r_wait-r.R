.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(sys))
cat(r_wait(c("--vanilla", "-q", "--slave", "-e", "quit(status=3)"), std_out = FALSE, std_err = FALSE), "\n")
