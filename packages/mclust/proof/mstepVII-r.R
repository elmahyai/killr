suppressPackageStartupMessages(library(mclust))
if (packageDescription("mclust")$Version != "6.1.3") stop("expected mclust 6.1.3")
myPrior <- function(data, G, modelName, shrinkage, mean, scale, dof) {
  list(shrinkage = shrinkage, mean = mean, scale = scale, dof = dof)
}
i <- 1:40
x <- cbind(sin(i), 0.7 * cos(i) + 0.1 * i, 0.5 * sin(1.3 * i) + i / 20)
w <- cbind(1 + cos(i), 2 + sin(i / 2), 1.5 + cos(i / 3))
s3 <- w[, 1] + w[, 2] + w[, 3]
z3 <- w / s3
s2 <- w[, 1] + w[, 2]
z2 <- cbind(w[, 1], w[, 2]) / s2
pri <- list(functionName = myPrior, shrinkage = 0.5, mean = c(0.1, -0.2, 0.3), scale = 2, dof = 5)
pack <- function(m) {
  v <- m$parameters
  c(as.vector(v$pro), as.vector(v$mean), as.vector(v$variance$sigmasq),
    as.vector(v$variance$sigma), attr(m, "returnCode"))
}
one <- function() {
  a1 <- mstepVII(x, z3)
  a2 <- mstepVII(x, z2)
  a3 <- mstepVII(x, z3, prior = pri)
  c(pack(a1), pack(a2), pack(a3))
}
value <- one()
elapsed <- numeric(20)
for (k in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[k] <- as.numeric(Sys.time()) - t0
}
cat(sprintf("%.17g\n", value), sep = "")
cat(sprintf("%.17g\n", median(elapsed) * 1000))
