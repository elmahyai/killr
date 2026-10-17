.libPaths(c(path.expand("~/R/library"), .libPaths()))
library(rlang)
cat(paste(as.character(c(is_logical(TRUE), is_logical(1))), collapse=','))
