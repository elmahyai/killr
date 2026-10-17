.libPaths(c(path.expand("~/R/library"), .libPaths()))
library(rlang)
cat(paste(as.character(is_scalar_logical(TRUE)), collapse=','))
