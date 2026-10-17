.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(sys))
pid <- r_background(c("--vanilla", "-q", "--slave", "-e", "quit(status=0)"), std_out = FALSE, std_err = FALSE); cat(exec_status(pid, wait = TRUE), "\n")
