suppressPackageStartupMessages(library(mclust))
if (packageDescription("mclust")$Version != "6.1.3") stop("expected mclust 6.1.3")

# Fixed inputs.
# Case A: one-dimensional, n = 40, G = 2 (E, V, X models).
# Case B: two-dimensional, n = 40, G = 2.
# Case C: three-dimensional, n = 60, G = 3.
ia <- seq_len(40L); ga <- as.numeric(ia > 20L)
wa <- ((ia * 7L) %% 19L) / 19
za <- cbind(0.2 + 0.6 * wa, 0.8 - 0.6 * wa)
xa <- ((ia * 37L) %% 11L) / 11 + 2.5 * ga
xb <- cbind(((ia * 37L) %% 11L) / 11 + 2.5 * ga,
            ((ia * 23L) %% 13L) / 13 + 1.5 * ga)
ic <- seq_len(60L)
xc <- matrix(0, 60L, 3L)
for (j in 1:3) xc[, j] <- ((ic * (3L * j + 5L)) %% 17L) / 17 + 0.25 * ((ic + j) %% 3L)
rc <- matrix(0, 60L, 3L)
for (k in 1:3) rc[, k] <- 1 + ((ic * (k + 2L)) %% 7L)
zc <- rc / rowSums(rc)

one_d <- c("E", "V", "X")
multi <- c("EII", "VII", "EEI", "VEI", "EVI", "VVI", "EEE", "EVE", "VEE", "VVE",
           "EEV", "VEV", "EVV", "VVV", "XII", "XXI", "XXX")
specs <- list()
for (m in one_d) specs[[length(specs) + 1]] <- list(case = "A", model = m, data = xa, z = za)
for (m in multi) {
  specs[[length(specs) + 1]] <- list(case = "B", model = m, data = xb, z = za)
  specs[[length(specs) + 1]] <- list(case = "C", model = m, data = xc, z = zc)
}

fmt <- function(x) {
  x <- as.numeric(x)
  s <- sprintf("%.17g", x)
  s[is.na(x)] <- "nan"
  paste(s, collapse = " ")
}

fields_of <- function(o) {
  out <- list()
  rcode <- attr(o, "returnCode")
  if (is.null(rcode)) rcode <- o[["returnCode"]]
  out[["returnCode"]] <- rcode
  out[["loglik"]] <- o[["loglik"]]
  out[["z"]] <- o[["z"]]
  p <- o[["parameters"]]
  out[["pro"]] <- p[["pro"]]
  out[["mean"]] <- p[["mean"]]
  v <- p[["variance"]]
  for (nm in c("Sigma", "sigma", "sigmasq", "scale", "shape", "orientation",
               "cholsigma", "cholSigma")) {
    out[[nm]] <- v[[nm]]
  }
  out
}

run_all <- function() {
  lapply(specs, function(s) me_call(s))
}
me_call <- function(s) mclust:::me(s$data, s$model, s$z, warn = FALSE)

# One untimed call over all specs, which also gives the values to compare.
results <- run_all()
lines <- character(0)
for (i in seq_along(specs)) {
  f <- fields_of(results[[i]])
  for (nm in names(f)) {
    lines <- c(lines, paste0(specs[[i]]$case, "|", specs[[i]]$model, "|", nm,
                             "\t", fmt(f[[nm]])))
  }
}

elapsed <- numeric(20)
for (k in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  run_all()
  elapsed[k] <- as.numeric(Sys.time()) - t0
}
cat(lines, sep = "\n")
cat(sprintf("TIMING_MEDIAN_MS\t%.17g\n", median(elapsed) * 1000))
