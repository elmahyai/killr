.libPaths(c(path.expand("~/R/library"), .libPaths()))
library(vctrs)
cat(paste(c(vec_size(1:3), vec_size('a')), collapse=','))
