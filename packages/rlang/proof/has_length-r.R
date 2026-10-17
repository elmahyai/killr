.libPaths(c(path.expand("~/R/library"), .libPaths()))
library(rlang)
cat(paste(as.character(c(has_length(1:3, 3), has_length(1, 2))), collapse=','))
