
.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(haven))
suppressPackageStartupMessages(library(jsonlite))
json_val <- function(x) {
  if (is.null(x)) return("null")
  toJSON(x, auto_unbox = TRUE, null = "null", digits = 17)
}

one <- function() {
  x <- labelled(1:3, c(a = 1))
  attr(x, "format.stata") <- "%9.0g"
  z <- zap_formats(x)
  c(as.integer(is.null(attr(z, "format.stata"))), as.integer(!is.null(attr(z, "labels"))))
}
value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf('{"value":%s,"median_ms":%.17g}\n', json_val(value), median(elapsed) * 1000))
