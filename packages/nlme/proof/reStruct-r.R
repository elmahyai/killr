.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(nlme))

one <- function() {
  data(Pixel)
  rs1 <- reStruct(list(Dog = ~day, Side = ~1), data = Pixel)
  c(
    as.numeric(attr(rs1, "settings")),
    length(rs1),
    as.numeric(isInitialized(rs1)),
    vapply(rs1, function(el) as.numeric(isInitialized(el)), 0),
    vapply(rs1, function(el) length(Names(el)), 0),
    vapply(rs1, function(el) length(coef(el)), 0),
    as.numeric(Dim(rs1[[1]])),
    as.numeric(Dim(rs1[[2]])),
    as.numeric(dim(matrix(rs1[[1]]))),
    as.numeric(dim(matrix(rs1[[2]])))
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
