.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(nlme))

one <- function() {
  pd1 <- pdMat(diag(1:4), pdClass = "pdDiag")
  c(
    as.integer(isInitialized(pd1)),
    as.integer(Dim(pd1)[1]),
    as.integer(Dim(pd1)[2]),
    length(Names(pd1)),
    as.vector(pd1)
  )
}

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf(
  "{\"value\":[%s],\"median_ms\":%.17g}\n",
  paste(sprintf("%.17g", value), collapse = ","),
  median(elapsed) * 1000
))
