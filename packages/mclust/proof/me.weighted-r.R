.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(mclust))
if (packageDescription("mclust")$Version != "6.1.3") stop("expected mclust 6.1.3")

# Usage: Rscript proof/me.weighted-r.R <modelName>
# Fixed inputs, the same as me.weighted-py.py (no random numbers).
# E and V: one dimension, n = 40, G = 2.
# Other models: two dimensions, n = 40, G = 3.
# Case A: unit weights (weights = NULL). Case B: weights 1 + (i mod 5),
# which me.weighted rescales to a maximum of 1.
args <- commandArgs(trailingOnly = TRUE)
model <- args[1]

if (model %in% c("E", "V")) {
  n <- 40L; d <- 1L; G <- 2L
  i <- 1:n
  y <- matrix(i / 10 + ((i * i) %% 7) / 3, ncol = 1)
} else {
  n <- 40L; d <- 2L; G <- 3L
  i <- 1:n
  y <- cbind(i / 20 + ((i * 37) %% 23) / 5,
             ((i * 11) %% 17) / 4 - i / 30 + (i %% 3))
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

# Named blocks, flattened in a fixed order that the Python script repeats.
fit_values <- function(fit) {
  c(loglik = fit$loglik,
    bic = fit$bic,
    setNames(as.vector(fit$z), paste0("z", seq_len(n * G))),
    setNames(as.vector(fit$parameters$pro), paste0("pro", seq_len(G))),
    setNames(as.vector(fit$parameters$mean), paste0("mean", seq_len(d * G))),
    setNames(sigma_of(fit$parameters$variance),
             paste0("sigma", seq_along(sigma_of(fit$parameters$variance)))))
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
  nm <- names(vals)
  for (k in seq_along(vals)) {
    cat(sprintf("%s_%s %.17g\n", case, nm[[k]], vals[[k]]))
  }
}
cat(sprintf("r_ms %.17g\n", median(elapsed)))
