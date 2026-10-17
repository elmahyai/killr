suppressPackageStartupMessages(library(mclust))
if (packageDescription("mclust")$Version != "6.1.3") stop("expected mclust 6.1.3")

i <- seq_len(40L)
g <- as.numeric(i > 20L)
x1 <- ((i * 37L) %% 11L) / 11 + 2.5 * g
w <- ((i * 7L) %% 19L) / 19
z2 <- cbind(0.2 + 0.6 * w, 0.8 - 0.6 * w)
z3 <- cbind(0.9 * (0.2 + 0.6 * w), 0.9 * (0.8 - 0.6 * w), rep(0.1, 40L))

myPrior <- function(data, G, modelName, shrinkage, mean, scale, dof) {
  list(shrinkage = shrinkage, mean = mean, scale = scale, dof = dof)
}
prior_e <- list(functionName = "myPrior", shrinkage = 0.1, mean = 1.0, scale = 1.5, dof = 3)

flat <- function(r) {
  c(
    r$loglik,
    attr(r, "returnCode"),
    attr(r, "info")[["iterations"]],
    attr(r, "info")[["error"]],
    r$parameters$variance$sigmasq,
    as.vector(r$parameters$mean),
    as.vector(r$parameters$pro),
    r$parameters$Vinv,
    as.vector(r$z)
  )
}

one <- function() {
  ctl <- emControl()
  a <- mclust:::meE(x1, z2, prior = NULL, control = ctl, Vinv = NULL, warn = FALSE)
  b <- mclust:::meE(x1, z2, prior = prior_e, control = ctl, Vinv = NULL, warn = FALSE)
  cc <- mclust:::meE(x1, z3, prior = NULL, control = ctl, Vinv = 0, warn = FALSE)
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
