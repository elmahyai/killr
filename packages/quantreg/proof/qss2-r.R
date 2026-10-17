suppressPackageStartupMessages({library(quantreg); library(SparseM)})
d <- as.matrix(read.table("/home/ahmed/killr_projects/killr/packages/quantreg/quantreg/data/check_design.txt"))
Xs <- cbind(c(0.1, 0.5, 0.9, 0.3, 0.7, 0.2), c(0.2, 0.4, 0.1, 0.8, 0.6, 0.3))
X <- cbind(d[, 2], d[, 3])
vec <- function(v) if (is.null(v)) c(-1) else c(length(v), as.numeric(v))
mat <- function(M) if (is.null(M)) c(-1) else { A <- as.matrix(M); c(dim(A), as.vector(t(A))) }
pack <- function(s) c(vec(s$x$x), vec(s$x$y), mat(s$F), mat(s$A), s$lambda, mat(s$R), vec(s$r))
one <- function() {
  n <- qss2(Xs, constraint = "N", lambda = 2)
  v <- qss2(X, constraint = "V", lambda = 1.5)
  cc <- qss2(X, constraint = "C", lambda = 0.5)
  c(pack(n), pack(v), pack(cc))
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
