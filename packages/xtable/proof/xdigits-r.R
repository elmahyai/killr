suppressPackageStartupMessages(library(xtable))
suppressPackageStartupMessages(library(jsonlite))
stopifnot(packageDescription("xtable")$Version == "1.8-8")

make_xt <- function(i) {
  n <- 3 + (i %% 4)
  xtable(data.frame(
    a = seq_len(n),
    b = seq_len(n) + 0.5,
    c = letters[seq_len(n)]
  ))
}

one <- function() {
  out <- list()
  for (i in 0:5) {
    x <- make_xt(i)
    out[[paste0("xdigits_", i)]] <- xdigits(x)
    out[[paste0("xdigits_zap_", i)]] <- xdigits(x, zap = 4)
  }
  out$vec <- xdigits(c(1.1, 2.22, 3))
  out$with_na <- xdigits(c(1.5, NA, 2.333))
  out$mat <- xdigits(matrix(c(1, 2.5, 3.01, 4), 2, 2))
  out
}

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf('{"median_ms":%.17g,"value":', median(elapsed) * 1000))
cat(toJSON(value, auto_unbox = FALSE, na = "null", null = "null"))
cat("}\n")
