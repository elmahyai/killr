.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(MASS))
one <- function() {
  x <- matrix(
    c(12, 5, 7, 3, 8, 15, 4, 9, 6, 11, 2, 10),
    nrow = 4,
    ncol = 3,
    dimnames = list(
      Row = c("R1", "R2", "R3", "R4"),
      Col = c("C1", "C2", "C3")
    )
  )
  ct <- corresp(x, nf = 2)
  c(
    as.vector(ct$cor),
    as.vector(ct$rscore),
    as.vector(ct$cscore),
    as.vector(ct$Freq)
  )
}
value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf("%.17g\n", as.numeric(value)))
cat(sprintf("%.17g\n", median(elapsed) * 1000))
