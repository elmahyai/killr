.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(fastmatch))
if (as.character(packageVersion("fastmatch")) != "1.1.8") stop("expected fastmatch 1.1-8")
options(warn = -1)
one <- function() {
  result <- ctapply(c(10, 11, 20, 21, 22), c(1L, 1L, 2L, 2L, 2L), sum)
  paste(names(result), result, sep = ":", collapse = "|")
}
value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(jsonlite::toJSON(list(value = value, median_ms = median(elapsed) * 1000), auto_unbox = FALSE, digits = 17, na = "null"))
