.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(fastmatch))
if (as.character(packageVersion("fastmatch")) != "1.1.8") stop("expected fastmatch 1.1-8")
options(warn = -1)
one <- function() {
  c(
    fmatch(c(1, NA, NaN, -0, 0, 2.5), c(0, NA, NaN, 2.5)),
    fmatch(4L, 1:3, nomatch = 0)
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
