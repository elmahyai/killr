.libPaths(c(path.expand("~/R/library"), .libPaths()))
library(openssl)
cat(length(aes_keygen(16)))
