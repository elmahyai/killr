.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(mclust))
if (packageDescription("mclust")$Version != "6.1.3") stop("expected mclust 6.1.3")

# Usage: Rscript proof/me.weighted-3d-alias-r.R <modelName>
# EEE and VVV use deterministic 3-D data with G = 3. X uses 1-D data
# with G = 2; XII, XXI, and XXX use the same 3-D data with G = 3.
model <- commandArgs(trailingOnly = TRUE)[1]
i <- 1:40
if (model == "X") {
  n <- 40L; d <- 1L; G <- 2L
  y <- matrix(i / 10 + ((i * i) %% 7) / 3, ncol = 1)
} else {
  n <- 40L; d <- 3L; G <- 3L
  y <- cbind(
    i / 20 + ((i * 37) %% 23) / 5,
    ((i * 11) %% 17) / 4 - i / 30 + (i %% 3),
    i / 13 + ((i * 7) %% 19) / 6 - (i %% 4) / 5
  )
}
raw <- matrix(0, n, G)
for (j in seq_len(G)) {
  raw[, j] <- 1 + 2 * ((i %% G) + 1 == j) + 0.3 * ((i + j) %% 4)
}
z <- raw / rowSums(raw)
w <- 1 + (i %% 5)

sigma_of <- function(v) {
  s <- v$sigma
  if (is.null(s)) s <- v$sigmasq
  as.vector(s)
}

fit_values <- function(fit) {
  c(
    loglik = fit$loglik,
    bic = fit$bic,
    setNames(as.vector(fit$z), paste0("z", seq_len(n * G))),
    setNames(as.vector(fit$parameters$pro), paste0("pro", seq_len(G))),
    setNames(as.vector(fit$parameters$mean), paste0("mean", seq_len(d * G))),
    setNames(sigma_of(fit$parameters$variance),
             paste0("sigma", seq_along(sigma_of(fit$parameters$variance))))
  )
}

one <- function() {
  a <- me.weighted(y, model, z)
  b <- me.weighted(y, model, z, weights = w)
  list(A = fit_values(a), B = fit_values(b))
}

res <- one()
elapsed <- numeric(20)
for (k in seq_len(20)) {
  t0 <- Sys.time()
  one()
  elapsed[[k]] <- as.numeric(Sys.time() - t0, units = "secs") * 1000
}
for (case in c("A", "B")) {
  vals <- res[[case]]
  for (k in seq_along(vals)) {
    cat(sprintf("%s_%s %.17g\n", case, names(vals)[k], vals[[k]]))
  }
}
cat(sprintf("r_ms %.17g\n", median(elapsed)))
