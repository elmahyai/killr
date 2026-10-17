.libPaths(c(path.expand("~/R/library"), .libPaths()))
library(curl)
cat(paste(names(multi_fdset(new_pool())), collapse=','))
