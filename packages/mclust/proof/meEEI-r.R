suppressPackageStartupMessages(library(mclust))
if (packageDescription("mclust")$Version != "6.1.3") stop("expected mclust 6.1.3")

i <- seq_len(40L)
g <- as.numeric(i > 20L)
x1 <- ((i * 37L) %% 11L) / 11 + 2.5 * g
x2 <- ((i * 23L) %% 13L) / 13 + 1.5 * g
X <- cbind(x1, x2)
w <- ((i * 7L) %% 19L) / 19
z2 <- cbind(0.2 + 0.6 * w, 0.8 - 0.6 * w)
z3 <- cbind(0.9 * (0.2 + 0.6 * w), 0.9 * (0.8 - 0.6 * w), rep(0.1, 40L))

myPrior <- function(data, G, modelName, shrinkage, mean, scale, dof) {
  list(shrinkage = shrinkage, mean = mean, scale = scale, dof = dof)
}
prior_p <- list(functionName = "myPrior", shrinkage = 0.1, mean = c(1.2, 0.8), scale = 0.9, dof = 4)

flat <- function(r) {
  c(
    r$loglik,
    attr(r, "returnCode"),
    attr(r, "info")[["iterations"]],
    attr(r, "info")[["error"]],
    r$parameters$variance$scale,
    as.vector(r$parameters$variance$shape),
    as.vector(r$parameters$mean),
    as.vector(r$parameters$pro),
    as.vector(r$parameters$variance$Sigma),
    as.vector(r$parameters$variance$sigma),
    r$parameters$Vinv,
    as.vector(r$z)
  )
}

one <- function() {
  ctl <- emControl()
  a <- mclust:::meEEI(X, z2, prior = NULL, control = ctl, Vinv = NULL, warn = FALSE)
  b <- mclust:::meEEI(X, z2, prior = prior_p, control = ctl, Vinv = NULL, warn = FALSE)
  cc <- mclust:::meEEI(X, z3, prior = NULL, control = ctl, Vinv = 0, warn = FALSE)
  c(flat(a), flat(b), flat(cc))
}

value <- one()
elapsed <- numeric(20)
for (k in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[k]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf("%.17g\n", value), sep = "")
cat(sprintf("%.17g\n", median(elapsed) * 1000))
