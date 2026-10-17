.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(fastmatch))
if (as.character(packageVersion("fastmatch")) != "1.1.8") stop("expected fastmatch 1.1-8")
options(warn = -1)
one <- function() {
  c(
    coalesce(c("b", "a", "b", "a", "c")),
    coalesce(c(1.5, 0, -0, 1.5, 2))
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
