.libPaths(c(path.expand("~/R/library"), path.expand("~/R/x86_64-pc-linux-gnu-library/4.5"), .libPaths()))
suppressPackageStartupMessages(library(urca))
if (as.character(packageVersion("urca")) != "1.3.4") stop("expected urca 1.3-4")
options(warn = -1)
data(denmark)
sjd <- denmark[, c("LRM", "LRY", "IBO", "IDE")]

one <- function() {
  fit <- cajolst(sjd, trend = TRUE, K = 2, season = 4)
  c(
    fit@bp,
    fit@teststat,
    fit@lambda,
    as.numeric(fit@V),
    as.numeric(fit@W),
    as.numeric(fit@cval)
  )
}

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(jsonlite::toJSON(list(value = value, median_ms = median(elapsed) * 1000), auto_unbox = FALSE, digits = 17, na = "null"))
