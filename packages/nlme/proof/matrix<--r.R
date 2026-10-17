.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(nlme))

one <- function() {
  data(Pixel)
  M <- matrix(c(2, 0.5, 0.5, 1), 2)
  p <- pdMat(nam = c("a", "b"), pdClass = "pdSymm")
  matrix(p) <- M
  q <- pdMat(nam = c("a", "b"), pdClass = "pdLogChol")
  matrix(q) <- M
  rs1 <- reStruct(list(Dog = ~day, Side = ~1), data = Pixel)
  matrix(rs1) <- list(diag(c(4, 2)), matrix(3))
  c(
    as.numeric(matrix(p)),
    as.numeric(matrix(q)),
    as.numeric(dim(matrix(p))),
    as.numeric(matrix(rs1[[1]])),
    as.numeric(matrix(rs1[[2]]))
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
