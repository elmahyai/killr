.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(sys))
cat(paste(windows_quote(c("a", "", "a b")), collapse = "|"), "\n")
