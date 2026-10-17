.libPaths(c(path.expand("~/R/library"), .libPaths()))
library(curl)
path <- tempfile(); writeBin(charToRaw("abc"), path)
h <- new_handle(); curl_fetch_memory(paste0("file://", path), h); handle_reset(h); cat(if (is.null(handle_data(h)$url) || !nzchar(handle_data(h)$url)) "TRUE" else "FALSE")
