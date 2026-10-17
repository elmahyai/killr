.libPaths(c(path.expand("~/R/library"), .libPaths()))
library(rlang)
cat(paste(as.character(c(is_double(1), is_double(1L))), collapse=','))
