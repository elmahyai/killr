.libPaths(c(path.expand("~/R/library"), .libPaths()))
library(curl)
cat(paste(names(handle_cookies(new_handle())), collapse=','))
