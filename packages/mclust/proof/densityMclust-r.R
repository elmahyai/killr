# Proof: R mclust::densityMclust (mclust 6.1.3) on fixed inputs. Run from packages/mclust:
#   Rscript proof/densityMclust-r.R
# plot = FALSE, so no figure is drawn. Writes docs/output/densityMclust-r.txt (tab-separated records)
# and the median of 20 timed calls (Sys.time) on the last line as time_ms.
suppressPackageStartupMessages(library(mclust))
if (packageDescription("mclust")$Version != "6.1.3") stop("expected mclust 6.1.3")

# Fixed inputs.
# Case A: banknote without the Status column, n = 200, d = 6, default G = 1:9 and
#         default modelNames (no duplicate rows, so dupPartition is 1:n).
# Case B: two-dimensional synthetic, n = 60, default G and modelNames.
# Case C: one-dimensional synthetic, n = 40, default G and modelNames (qclass start).
# Case D: the G = 1 path, two-dimensional, modelNames EII, VII, EEE, VVV.
# Case E: the G = 1 path, one-dimensional, modelNames E, V.
# Case F: one-dimensional bimodal, n = 80, default G (best model has G = 2, qclass start).
xa_bank <- as.matrix(read.csv(file.path("proof", "mclust_fit_banknote6.csv"), header = FALSE))
ib <- seq_len(60L)
xb <- cbind(((ib * 37L) %% 11L) / 11 + 0.05 * ib / 60,
            ((ib * 23L) %% 13L) / 13 - 0.1 * ib / 60)
ia <- seq_len(40L)
xc <- ((ia * 37L) %% 11L) / 11 + 0.1 * ia / 40
xf <- c(((ia * 37L) %% 11L) / 11 + 0.1 * ia / 40, 5 + ((ia * 23L) %% 13L) / 13 - 0.1 * ia / 40)

fmt <- function(x) ifelse(is.na(x), "NA", sprintf("%.17g", as.numeric(x)))

rec <- function(key, x) {
  if (is.null(x)) return(paste(key, "NULL", sep = "\t"))
  if (is.character(x)) return(paste(key, paste(x, collapse = "\t"), sep = "\t"))
  paste(c(key, fmt(as.vector(x))), collapse = "\t")
}

emit_fit <- function(prefix, fit) {
  v <- fit$parameters$variance
  var_vals <- if (!is.null(v[["sigmasq"]])) v[["sigmasq"]] else v[["sigma"]]
  c(
    rec(paste(prefix, "modelName", sep = "\t"), fit$modelName),
    rec(paste(prefix, "n", sep = "\t"), fit$n),
    rec(paste(prefix, "d", sep = "\t"), fit$d),
    rec(paste(prefix, "G", sep = "\t"), fit$G),
    rec(paste(prefix, "BICdim", sep = "\t"), dim(fit$BIC)),
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

one <- function() {
  list(
    A = suppressWarnings(densityMclust(xa_bank, plot = FALSE)),
    B = suppressWarnings(densityMclust(xb, plot = FALSE)),
    C = suppressWarnings(densityMclust(xc, plot = FALSE)),
    D = suppressWarnings(densityMclust(xb, G = 1, modelNames = c("EII", "VII", "EEE", "VVV"), plot = FALSE)),
    E = suppressWarnings(densityMclust(xc, G = 1, modelNames = c("E", "V"), plot = FALSE)),
    F = suppressWarnings(densityMclust(xf, plot = FALSE))
  )
}

fits <- one()
lines <- c(
  emit_fit("A", fits$A), emit_fit("B", fits$B), emit_fit("C", fits$C),
  emit_fit("D", fits$D), emit_fit("E", fits$E), emit_fit("F", fits$F)
)

elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- (as.numeric(Sys.time()) - t0) * 1000
}
lines <- c(lines, paste("time_ms", fmt(median(elapsed)), sep = "\t"))

dir.create(file.path("docs", "output"), recursive = TRUE, showWarnings = FALSE)
writeLines(lines, file.path("docs", "output", "densityMclust-r.txt"))
cat("R densityMclust median ms:", median(elapsed), "\n")
