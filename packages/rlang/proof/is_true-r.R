.libPaths(c(path.expand("~/R/library"), .libPaths()))
library(rlang)
cat(paste(as.character(c(is_true(TRUE), is_true(c(TRUE, TRUE)))), collapse=','))
