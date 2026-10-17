suppressPackageStartupMessages({library(quantreg); library(SparseM)})
d <- as.matrix(read.table("/home/ahmed/killr_projects/killr/packages/quantreg/quantreg/data/check_design.txt"))
xa <- c(0.1, 0.5, 0.1, 0.9, 0.5, 0.3, 0.7, 0.2)
ya <- c(0.2, 0.4, 0.2, 0.1, 0.4, 0.8, 0.6, 0.3)
xc <- d[1:6, 2]
yc <- d[1:6, 3]
dums <- list(x = c(0.25, 0.65), y = c(0.5, 0.45))
flat <- function(F) { M <- as.matrix(F); c(dim(M), as.vector(t(M))) }
one <- function() {
  a <- triogram.fidelity(xa, ya)
  b <- triogram.fidelity(xa, ya, dummies = dums)
  c0 <- triogram.fidelity(xc, yc)
  c(a$x, a$y, flat(a$F),
    b$x, b$y, flat(b$F), b$dummies$x, b$dummies$y,
    c0$x, c0$y, flat(c0$F))
}
invisible(one())
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
value <- one()
cat(paste(sprintf("%.17g", as.numeric(value)), collapse=","), "\n")
cat(sprintf("%.17g\n", median(elapsed) * 1000))
