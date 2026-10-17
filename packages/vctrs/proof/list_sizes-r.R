.libPaths(c(path.expand("~/R/library"), .libPaths()))
library(vctrs)
cat(paste(list_sizes(list(1:2, 3, integer())), collapse=','))
