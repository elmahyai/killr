.libPaths(c(path.expand("~/R/library"), .libPaths()))
library(curl)
path <- tempfile(); writeBin(charToRaw("abc"), path)
h <- new_handle(); curl_fetch_memory(paste0("file://", path), h); cat(handle_data(h)$status_code)
