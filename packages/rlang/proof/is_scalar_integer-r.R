.libPaths(c(path.expand("~/R/library"), .libPaths()))
library(rlang)
cat(paste(as.character(c(is_scalar_integer(1L), is_scalar_integer(1))), collapse=','))
