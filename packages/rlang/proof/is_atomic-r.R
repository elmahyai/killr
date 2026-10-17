.libPaths(c(path.expand("~/R/library"), .libPaths()))
library(rlang)
cat(paste(as.character(c(is_atomic(1), is_atomic(list(1)))), collapse=','))
