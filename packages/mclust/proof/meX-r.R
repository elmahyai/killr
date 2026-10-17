suppressPackageStartupMessages(library(mclust))
if (packageDescription("mclust")$Version != "6.1.3") stop("expected mclust 6.1.3")
n <- 60L
i <- 1:n
x <- sin(0.37 * i) + 0.3 * cos(1.7 * i) + 0.02 * i
one <- function() {
  out <- mclust:::meX(x)
  c(attr(out, "returnCode"), out$loglik, as.numeric(out$parameters$mean),
    out$parameters$variance$sigmasq, out$parameters$pro)
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
