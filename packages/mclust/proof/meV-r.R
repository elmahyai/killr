.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(mclust))
if (packageDescription("mclust")$Version != "6.1.3") stop("expected mclust 6.1.3")

meV <- mclust:::meV

pack <- function(fit) {
  c(
    as.numeric(fit$z),
    as.numeric(fit$parameters$mean),
    as.numeric(fit$parameters$variance$sigmasq),
    as.numeric(fit$parameters$pro),
    as.numeric(fit$loglik),
    as.numeric(attr(fit, "info")),
    as.numeric(attr(fit, "returnCode"))
  )
}

one <- function() {
  idx <- seq_len(60)
  x1 <- sin(idx * 0.37) * 1.3 + ifelse(idx %% 2 == 0, 3, -2)
  zu <- 1 / (1 + exp(-(x1 - 0.5) * 1.5))
  ZU <- cbind(zu, 1 - zu)
  c(pack(meV(x1, ZU)), pack(meV(x1, ZU, prior = mclust::priorControl())))
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
