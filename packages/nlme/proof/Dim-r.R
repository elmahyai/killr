.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(nlme))

one <- function() {
  grp <- c(1, 1, 2, 2, 2, 3, 3, 3, 3)
  cs1 <- corAR1(0.3, form = ~ 1 | Subject)
  cs2 <- corExp(0.5, form = ~ x | Subject)
  c(
    Dim(matrix(1:6, 2)),
    Dim(pdMat(diag(3))),
    Dim(pdMat(diag(1:4), pdClass = "pdDiag")),
    unlist(Dim(cs1, groups = grp)),
    unlist(Dim(cs2, groups = grp))
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
