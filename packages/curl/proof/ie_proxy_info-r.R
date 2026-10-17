.libPaths(c(path.expand("~/R/library"), .libPaths()))
library(curl)
cat(if (is.null(ie_proxy_info())) 'NULL' else 'SET')
