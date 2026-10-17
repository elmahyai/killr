.libPaths(c(path.expand("~/R/library"), .libPaths()))
library(openssl)
m <- multihash('foo', c('md5','sha1')); cat(paste(m$md5, m$sha1))
