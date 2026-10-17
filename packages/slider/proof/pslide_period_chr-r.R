
.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(slider))
suppressPackageStartupMessages(library(jsonlite))
n <- 2000L
i <- as.Date("2010-01-01") + 0:(n - 1L)
x <- letters[((seq_len(n) - 1L) %% 26L) + 1L]
y <- letters[((seq_len(n) + 12L) %% 26L) + 1L]
json_val <- function(value) {
  toJSON(value, auto_unbox = FALSE, na = "null")
}

one <- function() {
  pslide_period_chr(
    list(x, y),
    i,
    "month",
    function(a, b) paste0(paste(a, collapse = ""), "|", paste(b, collapse = "")),
    .before = 1L
  )
}
value <- one()
elapsed <- numeric(20)
for (step_i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[step_i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf('{"value":%s,"median_ms":%.17g}\n', json_val(value), median(elapsed) * 1000))
