.libPaths(c(path.expand("~/R/library"), .libPaths()))
library(curl)
path <- tempfile(); writeBin(charToRaw("abc"), path)
chunks <- raw(); curl_fetch_stream(paste0("file://", path), function(x) chunks <<- c(chunks, x)); cat(rawToChar(chunks))
