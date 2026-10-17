.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(sys))
cat(paste(as_text(charToRaw("a\nb\n")), collapse = "|"), "\n")
