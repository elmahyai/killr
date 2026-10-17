.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(sys))
pid <- exec_background("false", std_out = FALSE, std_err = FALSE); Sys.sleep(0.05); cat("false wait status ", exec_status(pid, wait = TRUE), "\n", sep = "")
