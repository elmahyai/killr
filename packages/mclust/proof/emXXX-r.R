suppressPackageStartupMessages(library(mclust))
if (packageDescription("mclust")$Version != "6.1.3") stop("expected mclust 6.1.3")

# Fixed inputs. Case A is 6 x 4, B is 60 x 3 (as in meXXX-r.R).
case_a <- matrix(c(-1.2, 0.5, 2.1, 1.7, -0.3, 0.9, 3.2, 1.1, 0.4, -0.8, 1.3, 2.6,
                   2.2, 1.5, -1.1, 0.7, 1.1, -1.7, 0.2, 3.4, 3.3, 0.2, 2.4, -0.5),
                 ncol = 4, byrow = TRUE)
make_b <- function() {
  n <- 60L; p <- 3L
  x <- matrix(0, n, p)
  for (i in 1:n) for (j in 1:p) x[i, j] <- sin(0.37 * i + 1.3 * j) + 0.4 * cos(0.11 * i * j) + 0.05 * i / n * j
  x
}
case_b <- make_b()

num <- function(x) as.numeric(unlist(x))
flat_out <- function(out) {
  v <- out[["parameters"]][["variance"]]
  c(num(attr(out, "returnCode")),
    num(out[["loglik"]]),
    num(out[["parameters"]][["mean"]]),
    num(v[["Sigma"]]),
    num(v[["cholSigma"]]))
}

one <- function() {
  a <- emXXX(case_a)
  b <- emXXX(case_b)
  c(flat_out(a), flat_out(b))
}

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf("%.17g\n", value), sep = "")
cat(sprintf("%.17g\n", median(elapsed) * 1000))
