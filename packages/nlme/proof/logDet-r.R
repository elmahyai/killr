.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(nlme))

one <- function() {
  data(Pixel)
  M <- matrix(c(2, 0.5, 0.5, 1), 2)
  s <- pdMat(M, nam = c("a", "b"), pdClass = "pdSymm")
  l <- pdMat(M, nam = c("a", "b"), pdClass = "pdLogChol")
  d <- pdMat(diag(c(2, 3)), nam = c("a", "b"), pdClass = "pdDiag")
  i <- pdMat(2 * diag(2), nam = c("a", "b"), pdClass = "pdIdent")
  cs <- pdMat(matrix(c(2, 0.6, 0.6, 2), 2), nam = c("a", "b"),
              pdClass = "pdCompSymm")
  rs1 <- reStruct(list(Dog = ~day, Side = ~1), data = Pixel)
  matrix(rs1) <- list(diag(c(4, 2)), matrix(3))
  dat <- data.frame(
    x = c(0, 1, 0.5, 2),
    y = c(0, 0, 1, 0.5)
  )
  small <- data.frame(g = rep(1, 3))
  comp <- Initialize(corCompSymm(0.2, ~1 | g), small)
  symm <- Initialize(corSymm(c(0, 0, 0), ~1 | g), small)
  lin <- Initialize(corLin(2.5, ~x + y), dat)
  ratio <- Initialize(corRatio(1.8, ~x + y), dat)
  spher <- Initialize(corSpher(2.5, ~x + y), dat)
  c(
    logDet(s),
    logDet(l),
    logDet(d),
    logDet(i),
    logDet(cs),
    logDet(rs1),
    logDet(corIdent()),
    logDet(comp),
    logDet(symm),
    logDet(lin),
    logDet(ratio),
    logDet(spher)
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
