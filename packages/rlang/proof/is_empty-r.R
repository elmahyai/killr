.libPaths(c(path.expand("~/R/library"), .libPaths()))
library(rlang)
cat(paste(as.character(c(is_empty(NULL), is_empty(integer(0)), is_empty(1))), collapse=','))
