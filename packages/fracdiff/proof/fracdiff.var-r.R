.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(fracdiff))
if (as.character(packageVersion("fracdiff")) != "1.5.4") stop("expected fracdiff 1.5-4")
options(warn = -1)
one <- function() {
  fit <- fracdiff(sin(1:40) + 0.3 * cos((1:40) / 3)); as.numeric(fracdiff.var(sin(1:40) + 0.3 * cos((1:40) / 3), fit, h = 0.01)$stderror.dpq)
}
value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(jsonlite::toJSON(list(value = value, median_ms = median(elapsed) * 1000), auto_unbox = FALSE, digits = 17, na = "null"))
