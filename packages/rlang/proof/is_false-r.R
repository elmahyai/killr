.libPaths(c(path.expand("~/R/library"), .libPaths()))
library(rlang)
cat(paste(as.character(c(is_false(FALSE), is_false(NA))), collapse=','))
