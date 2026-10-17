.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(fracdiff))
if (as.character(packageVersion("fracdiff")) != "1.5.4") stop("expected fracdiff 1.5-4")
options(warn = -1)
one <- function() {
  diffseries(sin(1:40) + 0.3 * cos((1:40) / 3), 0.25)
}
value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(jsonlite::toJSON(list(value = value, median_ms = median(elapsed) * 1000), auto_unbox = FALSE, digits = 17, na = "null"))
