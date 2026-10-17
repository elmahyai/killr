.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(askpass))
cat(if (is.null(ssh_askpass())) "NULL\n" else "SET\n")
