.libPaths(c(path.expand("~/R/library"), .libPaths()))
library(curl)
cat(length(ie_get_proxy_for_url('http://example.com')))
