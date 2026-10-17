.libPaths(c(path.expand("~/R/library"), .libPaths()))
library(openssl)
cat(if (is.null(askpass('x'))) 'NULL' else 'SET')
