.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(nlme))

one <- function() {
  data(Pixel)
  rs1 <- reStruct(list(Dog = ~day, Side = ~1), data = Pixel)
  p0 <- pdMat(nam = c("a", "b"))
  p1 <- pdMat(diag(2), nam = c("a", "b"))
  c(
    as.numeric(isInitialized(rs1)),
    vapply(rs1, function(el) as.numeric(isInitialized(el)), 0),
    as.numeric(isInitialized(p0)),
    as.numeric(isInitialized(p1)),
    as.numeric(isInitialized(rs1[[1]]))
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
