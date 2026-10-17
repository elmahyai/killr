
.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(slider))
suppressPackageStartupMessages(library(jsonlite))
x <- 1:6
i <- as.Date("2019-01-01") + c(-2:2, 31)
json_val <- function(value) {
  toJSON(as.numeric(value), auto_unbox = FALSE, digits = 17, na = "null")
}

one <- function() {
  as.numeric(unlist(block(x, i, period = "year")))
}
value <- one()
elapsed <- numeric(20)
for (step_i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[step_i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf('{"value":%s,"median_ms":%.17g}\n', json_val(value), median(elapsed) * 1000))
