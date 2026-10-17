# Proof: R mclust::MclustBootstrap (mclust 6.1.3) for types "wlbs", "pb" and "jk".
# Run from packages/mclust:
#   Rscript proof/MclustBootstrap-types-r.R
# Writes docs/output/MclustBootstrap-types-r.txt: one record per line, tab-separated.
# For each type, seeds 42 and 2026 are run with set.seed() right before the call,
# and the median of 20 timed calls (Sys.time, seed 42) is the line <type> time_ms.
suppressPackageStartupMessages(library(mclust))
if (packageDescription("mclust")$Version != "6.1.3") stop("expected mclust 6.1.3")
if (RNGkind()[1] != "Mersenne-Twister" || RNGkind()[3] != "Rejection") stop("expected default RNG kinds")

# Same fixed input as proof/MclustBootstrap-r.R: n = 60, d = 2, no duplicate rows.
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
run <- function(type, seed) {
  set.seed(seed)
  suppressWarnings(MclustBootstrap(fit, type = type))
}

emit <- function(type, label, b) {
  p <- paste(type, label, sep = "\t")
  c(
    rec(paste(p, "modelName", sep = "\t"), b$modelName),
    rec(paste(p, "G", sep = "\t"), b$G),
    rec(paste(p, "nboot", sep = "\t"), b$nboot),
    rec(paste(p, "type", sep = "\t"), b$type),
    rec(paste(p, "nonfit", sep = "\t"), b$nonfit),
    rec(paste(p, "par_pro", sep = "\t"), b$parameters$pro),
    rec(paste(p, "par_mean", sep = "\t"), b$parameters$mean),
    rec(paste(p, "par_variance", sep = "\t"), b$parameters$variance),
    rec(paste(p, "pro", sep = "\t"), b$pro),
    rec(paste(p, "mean", sep = "\t"), b$mean),
    rec(paste(p, "variance", sep = "\t"), b$variance)
  )
}

lines <- c(rec("fit\tmodelName", fit$modelName), rec("fit\tG", fit$G))
for (type in c("wlbs", "pb", "jk")) {
  lines <- c(lines,
             emit(type, "seed42", run(type, 42)),
             emit(type, "seed2026", run(type, 2026)))
  elapsed <- numeric(20)
  for (i in seq_len(20)) {
    t0 <- as.numeric(Sys.time())
    run(type, 42)
    elapsed[[i]] <- (as.numeric(Sys.time()) - t0) * 1000
  }
  lines <- c(lines, paste(type, "time_ms", fmt(median(elapsed)), sep = "\t"))
  cat("R MclustBootstrap", type, "median ms:", median(elapsed), "\n")
}

dir.create(file.path("docs", "output"), recursive = TRUE, showWarnings = FALSE)
writeLines(lines, file.path("docs", "output", "MclustBootstrap-types-r.txt"))
