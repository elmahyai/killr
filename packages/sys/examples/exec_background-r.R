.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(sys))
pid <- exec_background("true", std_out = FALSE, std_err = FALSE); Sys.sleep(0.05); cat(exec_status(pid, wait = TRUE), "\n")
