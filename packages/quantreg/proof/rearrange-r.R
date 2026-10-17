suppressPackageStartupMessages(library(quantreg))
kx <- c(0.5, 1.2, 1.2, 2.0, 3.1, 3.1, 4.5)
ky <- c(0.3, 1.0, 0.2, 2.5, 0.9, 1.7, 3.3, 0.4)
f1 <- stepfun(kx, ky)
f2 <- stepfun(kx, ky, right = TRUE)
grid <- c(-1, 0.5, 0.9, 1.2, 1.5, 2.0, 2.7, 3.1, 4.0, 4.5, 6)
one <- function() {
  r1 <- rearrange(f1)
  r2 <- rearrange(f2)
  r3 <- rearrange(f1, 1, 4)
  c(knots(r1), r1(grid), knots(r2), r2(grid), knots(r3), r3(grid))
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
