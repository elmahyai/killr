suppressPackageStartupMessages(library(mclust))
if (packageDescription("mclust")$Version != "6.1.3") stop("expected mclust 6.1.3")

# Fixed inputs: x is 60 x 3, as in emVVE-r.R.
n <- 60L
p <- 3L
x <- matrix(0, n, p)
for (i in 1:n) for (j in 1:p) x[i, j] <- sin(0.37 * i + 1.3 * j) + 0.4 * cos(0.11 * i * j) + 0.05 * i / n * j
mu <- matrix(c(0.1, -0.2, 0.3, 0.5, 0.4, -0.1), p, 2)

num <- function(x) as.numeric(unlist(x))
flat_out <- function(out) {
  v <- out[["parameters"]][["variance"]]
  info <- attr(out, "info")
  c(num(attr(out, "returnCode")),
    num(out[["loglik"]]),
    num(out[["parameters"]][["pro"]]),
    num(out[["parameters"]][["mean"]]),
    num(v[["scale"]]), num(v[["shape"]]), num(v[["sigmasq"]]),
    num(v[["orientation"]]), num(v[["sigma"]]),
    num(out[["z"]]),
    num(info), num(attr(info, "inner")))
}

one <- function() {
  a <- emVEI(x, list(pro = c(0.4, 0.6), mean = mu,
                     variance = list(scale = c(1.3, 0.7), shape = c(1.5, 0.6, 0.9))))
  b <- emVEI(x, list(pro = c(0.3, 0.45, 0.25), mean = mu,
                     variance = list(scale = c(1.3, 0.7), shape = c(1.5, 0.6, 0.9)),
                     Vinv = 0.1))
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
