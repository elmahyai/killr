.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(mclust))
if (packageDescription("mclust")$Version != "6.1.3") stop("expected mclust 6.1.3")

meVII <- mclust:::meVII

pack <- function(fit) {
  info <- attr(fit, "info")
  v <- fit$parameters$variance
  c(
    as.numeric(fit$z),
    as.numeric(fit$parameters$mean),
    as.numeric(v$sigmasq),
    as.numeric(fit$parameters$pro),
    as.numeric(v$sigma),
    as.numeric(fit$loglik),
    as.numeric(info),
    as.numeric(attr(fit, "returnCode"))
  )
}

one <- function() {
  idx <- seq_len(60)
  x1 <- sin(idx * 0.37) * 1.3 + ifelse(idx %% 2 == 0, 3, -2)
  x2 <- cos(idx * 0.53) * 1.1 + 0.4 * x1 + ifelse(idx %% 3 == 0, 2.5, 0)
  X <- cbind(x1, x2)
  z1 <- 1 / (1 + exp(-(x1 - 0) * 1.2))
  Z <- cbind(z1, 1 - z1)
  c(pack(meVII(X, Z)), pack(meVII(X, Z, prior = mclust::priorControl())))
}

value <- one()
elapsed <- numeric(20)
for (rep in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[rep]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf("%.17g\n", value), sep = "")
cat(sprintf("%.17g\n", median(elapsed) * 1000))
