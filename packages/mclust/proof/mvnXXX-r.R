suppressPackageStartupMessages(library(mclust))
if (packageDescription("mclust")$Version != "6.1.3") stop("expected mclust 6.1.3")

# Fixed inputs. Case A is 6 x 4, B is 60 x 3, C is 25 x 2.
case_a <- matrix(c(-1.2, 0.5, 2.1, 1.7, -0.3, 0.9, 3.2, 1.1, 0.4, -0.8, 1.3, 2.6,
                   2.2, 1.5, -1.1, 0.7, 1.1, -1.7, 0.2, 3.4, 3.3, 0.2, 2.4, -0.5),
                 ncol = 4, byrow = TRUE)
make_b <- function() {
  n <- 60L; p <- 3L
  x <- matrix(0, n, p)
  for (i in 1:n) for (j in 1:p) x[i, j] <- sin(0.37 * i + 1.3 * j) + 0.4 * cos(0.11 * i * j) + 0.05 * i / n * j
  x
}
make_c <- function() {
  n <- 25L; p <- 2L
  x <- matrix(0, n, p)
  for (i in 1:n) for (j in 1:p) x[i, j] <- cos(0.7 * i + j) + 0.2 * sin(1.9 * i * j) + 0.01 * i * j
  x
}
cases <- list(A = case_a, B = make_b(), C = make_c())

one <- function(x) {
  y <- mvnXXX(x)
  c(attr(y, "returnCode"), y$loglik, as.numeric(y$parameters$mean),
    as.numeric(y$parameters$variance$Sigma), as.numeric(y$parameters$variance$cholSigma))
}

vals <- unlist(lapply(cases, one))
primary <- cases$B
invisible(one(primary))
elapsed <- numeric(20)
for (k in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  invisible(one(primary))
  elapsed[k] <- as.numeric(Sys.time()) - t0
}
cat(sprintf("%.17g\n", vals), sep = "")
cat(sprintf("%.17g\n", median(elapsed) * 1000))
