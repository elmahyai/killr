.libPaths(c(path.expand("~/R/library"), .libPaths()))
library(curl)
path <- tempfile(); writeBin(charToRaw("abc"), path)
cat(rawToChar(readBin(curl_download(paste0("file://", path), tempfile()), raw(), 10)))
