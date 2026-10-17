.libPaths(c(path.expand("~/R/library"), .libPaths()))
library(curl)
path <- tempfile(); writeBin(charToRaw("abc"), path)
pool <- new_pool(); multi_add(new_handle(url=paste0("file://", path)), pool=pool); cat(length(multi_list(pool)))
