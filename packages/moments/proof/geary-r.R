.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(moments))
if (as.character(packageVersion("moments")) != "0.14.1") stop("expected moments 0.14.1")
options(warn = -1)
one <- function() {
  geary(c(1, 2, 4, -1, 5, 3, 8))
}
value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(jsonlite::toJSON(list(value = value, median_ms = median(elapsed) * 1000), auto_unbox = FALSE, digits = 17, na = "null"))
