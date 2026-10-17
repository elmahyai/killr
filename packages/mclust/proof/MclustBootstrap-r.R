# Proof: R mclust::MclustBootstrap (mclust 6.1.3), default call (type = "bs", nboot = 999).
# Run from packages/mclust:
#   Rscript proof/MclustBootstrap-r.R
# Writes docs/output/MclustBootstrap-r.txt: one record per line, tab-separated.
# The last line is time_ms, the median of 20 timed calls (Sys.time).
suppressPackageStartupMessages(library(mclust))
if (packageDescription("mclust")$Version != "6.1.3") stop("expected mclust 6.1.3")
if (RNGkind()[1] != "Mersenne-Twister" || RNGkind()[3] != "Rejection") stop("expected default RNG kinds")

# Fixed input: n = 60, d = 2, no duplicate rows, default Mclust (G = 1:9).
ib <- seq_len(60L)
xb <- cbind(((ib * 37L) %% 11L) / 11 + 0.05 * ib / 60,
            ((ib * 23L) %% 13L) / 13 - 0.1 * ib / 60)
if (anyDuplicated(xb)) stop("fixed input must have no duplicate rows")
fit <- suppressWarnings(Mclust(xb))

fmt <- function(x) ifelse(is.na(x), "NA", sprintf("%.17g", as.numeric(x)))

rec <- function(key, x) {
  if (is.null(x)) return(paste(key, "NULL", sep = "\t"))
  if (is.character(x)) return(paste(c(key, x), collapse = "\t"))
  paste(c(key, fmt(as.vector(x))), collapse = "\t")
}

# One bootstrap with set.seed(seed) right before the call.
run <- function(seed) {
  set.seed(seed)
  suppressWarnings(MclustBootstrap(fit))
}

emit <- function(prefix, b) {
  c(
    rec(paste(prefix, "modelName", sep = "\t"), b$modelName),
    rec(paste(prefix, "G", sep = "\t"), b$G),
    rec(paste(prefix, "nboot", sep = "\t"), b$nboot),
    rec(paste(prefix, "type", sep = "\t"), b$type),
    rec(paste(prefix, "nonfit", sep = "\t"), b$nonfit),
    rec(paste(prefix, "par_pro", sep = "\t"), b$parameters$pro),
    rec(paste(prefix, "par_mean", sep = "\t"), b$parameters$mean),
    rec(paste(prefix, "par_variance", sep = "\t"), b$parameters$variance),
    rec(paste(prefix, "pro", sep = "\t"), b$pro),
    rec(paste(prefix, "mean", sep = "\t"), b$mean),
    rec(paste(prefix, "variance", sep = "\t"), b$variance)
  )
}

# Untimed call (seed 42), plus seed 2026 as a second check on the same fit.
b42 <- run(42)
b2026 <- run(2026)
lines <- c(
  rec("fit\tmodelName", fit$modelName),
  rec("fit\tG", fit$G),
  emit("seed42", b42),
  emit("seed2026", b2026)
)

elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  run(42)
  elapsed[[i]] <- (as.numeric(Sys.time()) - t0) * 1000
}
lines <- c(lines, paste("time_ms", fmt(median(elapsed)), sep = "\t"))

dir.create(file.path("docs", "output"), recursive = TRUE, showWarnings = FALSE)
writeLines(lines, file.path("docs", "output", "MclustBootstrap-r.txt"))
cat("R MclustBootstrap median ms:", median(elapsed), "\n")
