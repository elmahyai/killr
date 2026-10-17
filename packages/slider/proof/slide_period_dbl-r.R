
.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(slider))
suppressPackageStartupMessages(library(jsonlite))
n <- 2000L
i <- as.Date("2010-01-01") + 0:(n - 1L)
json_val <- function(value) {
  toJSON(value, auto_unbox = FALSE, digits = 17, na = "null")
}

x <- as.numeric(seq_len(n))

one <- function() {
  slide_period_dbl(x, i, "month", function(w) sum(w), .before = 1L, .complete = TRUE)
}
value <- one()
elapsed <- numeric(20)
for (step_i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[step_i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf('{"type":"%s","value":%s,"median_ms":%.17g}\n', typeof(value), json_val(value), median(elapsed) * 1000))
