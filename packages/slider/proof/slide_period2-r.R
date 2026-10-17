
.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(slider))
suppressPackageStartupMessages(library(jsonlite))
n <- 2000L
i <- as.Date("2010-01-01") + 0:(n - 1L)
x <- seq_len(n)
y <- seq_len(n) + 100L
json_val <- function(value) {
  toJSON(as.numeric(value), auto_unbox = FALSE, digits = 17, na = "null")
}

one <- function() {
  as.numeric(unlist(slide_period2(x, y, i, "month", function(a, b) sum(a) + sum(b), .before = 1L)))
}
value <- one()
elapsed <- numeric(20)
for (step_i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[step_i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf('{"value":%s,"median_ms":%.17g}\n', json_val(value), median(elapsed) * 1000))
