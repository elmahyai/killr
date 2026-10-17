.libPaths(c(path.expand("~/R/library"), .libPaths()))
library(vctrs)
cat(paste(vec_slice(1:5, 2:3), collapse=','))
