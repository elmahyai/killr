.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(abind))
if (packageDescription("abind")$Version != "1.4-8") stop("expected abind 1.4-8")
one <- function() {
  x <- matrix(1:240, 15, 16)
  y <- matrix(241:480, 15, 16)
  along15 <- abind(x, y, along = 1.5)
  along1 <- abind(x, y, along = 1)
  along2 <- abind(x, y, along = 2)
  along0 <- abind(x, y, along = 0)
  c(dim(along15), dim(along1), dim(along2), dim(along0), as.numeric(along15), as.numeric(along1), as.numeric(along2), as.numeric(along0))
}
value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(jsonlite::toJSON(list(value = value, median_ms = median(elapsed) * 1000), auto_unbox = FALSE, digits = 17))
