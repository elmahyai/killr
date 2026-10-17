.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(askpass))
cat(if (is.null(askpass("x"))) "NULL\n" else "SET\n")
