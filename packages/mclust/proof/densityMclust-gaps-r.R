# Proof: R mclust::densityMclust (mclust 6.1.3) for the three gaps, on fixed inputs.
# Run from packages/mclust:
#   Rscript proof/densityMclust-gaps-r.R
# Writes docs/output/densityMclust-gaps-r.txt (tab-separated records) and the median of
# 20 timed calls (Sys.time) on the last line as time_ms.
#
# Cases A-F are the six inputs of Mclust-r.R. FA is faithful (16 duplicate rows).
# BIG is n = 2400 with set.seed(2026) (R draws a 2000-row initial subset).
# NB, NC are the noise model on xb and xc; NBV is the noise model with Vinv = 0.5.
suppressPackageStartupMessages(library(mclust))
if (packageDescription("mclust")$Version != "6.1.3") stop("expected mclust 6.1.3")

xa_bank <- as.matrix(read.csv(file.path("proof", "mclust_fit_banknote6.csv"), header = FALSE))
ib <- seq_len(60L)
xb <- cbind(((ib * 37L) %% 11L) / 11 + 0.05 * ib / 60,
            ((ib * 23L) %% 13L) / 13 - 0.1 * ib / 60)
ia <- seq_len(40L)
xc <- ((ia * 37L) %% 11L) / 11 + 0.1 * ia / 40
xf <- c(((ia * 37L) %% 11L) / 11 + 0.1 * ia / 40, 5 + ((ia * 23L) %% 13L) / 13 - 0.1 * ia / 40)
xfa <- as.matrix(read.csv(file.path("proof", "mclust_faithful.csv"), header = FALSE))
ig <- seq_len(2400L)
xg <- cbind(sin(0.37 * ig + 1.3) + 0.4 * cos(0.11 * ig) + 3 * (ig > 1200L),
            cos(0.23 * ig) + 0.5 * sin(0.07 * ig))
noise_b <- c(3L, 17L, 29L, 44L, 58L)
noise_c <- c(2L, 5L, 9L)

fmt <- function(x) ifelse(is.na(x), "NA", sprintf("%.17g", as.numeric(x)))

rec <- function(key, x) {
  if (is.null(x)) return(paste(key, "NULL", sep = "\t"))
  if (is.character(x)) return(paste(key, paste(x, collapse = "\t"), sep = "\t"))
  paste(c(key, fmt(as.vector(x))), collapse = "\t")
}

emit_fit <- function(prefix, fit) {
  if (identical(fit, "ERROR")) return(paste(prefix, "error", "ERROR", sep = "\t"))
  v <- fit$parameters$variance
  var_vals <- if (!is.null(v[["sigmasq"]])) v[["sigmasq"]] else v[["sigma"]]
  c(
    rec(paste(prefix, "modelName", sep = "\t"), fit$modelName),
    rec(paste(prefix, "n", sep = "\t"), fit$n),
    rec(paste(prefix, "d", sep = "\t"), fit$d),
    rec(paste(prefix, "G", sep = "\t"), fit$G),
    rec(paste(prefix, "BIC", sep = "\t"), unclass(fit$BIC)),
    rec(paste(prefix, "loglik", sep = "\t"), fit$loglik),
    rec(paste(prefix, "bic", sep = "\t"), fit$bic),
    rec(paste(prefix, "icl", sep = "\t"), fit$icl),
    rec(paste(prefix, "df", sep = "\t"), fit$df),
    rec(paste(prefix, "hypvol", sep = "\t"), fit$hypvol),
    rec(paste(prefix, "pro", sep = "\t"), fit$parameters$pro),
    rec(paste(prefix, "mean", sep = "\t"), fit$parameters$mean),
    rec(paste(prefix, "variance", sep = "\t"), var_vals),
    rec(paste(prefix, "z", sep = "\t"), fit$z),
    rec(paste(prefix, "classification", sep = "\t"), fit$classification),
    rec(paste(prefix, "uncertainty", sep = "\t"), fit$uncertainty),
    rec(paste(prefix, "density", sep = "\t"), fit$density)
  )
}

keys <- c("A", "B", "C", "D", "E", "F", "FA", "BIG", "NB", "NC", "NBV")

# A case that R rejects is recorded as ERROR (the message goes to the log).
guard <- function(expr) tryCatch(suppressWarnings(expr), error = function(e) {
  cat("case error:", conditionMessage(e), "\n")
  "ERROR"
})

one <- function() {
  list(
    A = guard(densityMclust(xa_bank, plot = FALSE)),
    B = guard(densityMclust(xb, plot = FALSE)),
    C = guard(densityMclust(xc, plot = FALSE)),
    D = guard(densityMclust(xb, G = 1, modelNames = c("EII", "VII", "EEE", "VVV"), plot = FALSE)),
    E = guard(densityMclust(xc, G = 1, modelNames = c("E", "V"), plot = FALSE)),
    F = guard(densityMclust(xf, plot = FALSE)),
    FA = guard(densityMclust(xfa, plot = FALSE)),
    BIG = { set.seed(2026); guard(densityMclust(xg, plot = FALSE)) },
    NB = guard(densityMclust(xb, initialization = list(noise = noise_b), plot = FALSE)),
    NC = guard(densityMclust(xc, initialization = list(noise = noise_c), plot = FALSE)),
    NBV = guard(densityMclust(xb, initialization = list(noise = noise_b), Vinv = 0.5, plot = FALSE))
  )
}

fits <- one()
lines <- character(0)
for (k in keys) lines <- c(lines, emit_fit(k, fits[[k]]))

elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- (as.numeric(Sys.time()) - t0) * 1000
}
lines <- c(lines, paste("time_ms", fmt(median(elapsed)), sep = "\t"))

dir.create(file.path("docs", "output"), recursive = TRUE, showWarnings = FALSE)
writeLines(lines, file.path("docs", "output", "densityMclust-gaps-r.txt"))
cat("R densityMclust gaps median ms:", median(elapsed), "\n")
