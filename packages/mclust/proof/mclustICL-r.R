# Proof: R mclust 6.1.3 mclustICL on fixed inputs. Run from packages/mclust:
#   Rscript proof/mclustICL-r.R
# Writes docs/output/mclustICL-r.txt: for each case, the ICL matrix (column-major),
# its G, modelNames, n, d, oneD, returnCodes and criterion, then time_ms, the
# median of 20 timed calls (Sys.time) over all cases.
suppressPackageStartupMessages(library(mclust))
if (packageDescription("mclust")$Version != "6.1.3") stop("expected mclust 6.1.3")

proof_dir <- "/home/ahmed/killr_projects/killr/packages/mclust/proof"
out_dir <- "/home/ahmed/killr_projects/killr/packages/mclust/docs/output"

# Inputs: the same formulas as mclustICL-py.py.
xfa <- as.matrix(read.csv(file.path(proof_dir, "mclust_faithful.csv"), header = FALSE))
ib <- seq_len(60L)
xb <- cbind(((ib * 37L) %% 11L) / 11 + 0.05 * ib / 60,
            ((ib * 23L) %% 13L) / 13 - 0.1 * ib / 60)
i3 <- seq_len(60L)
g3 <- (i3 - 1L) %% 3L
x3 <- cbind(1.3 * cos(0.37 * i3) + 2.5 * g3,
            0.9 * sin(0.53 * i3) + 0.8 * g3 - 0.5,
            0.4 * cos(0.9 * i3) + 0.2 * sin(1.7 * i3))
x1 <- xb[, 1]

models6 <- c("EII", "VII", "EEI", "VVI", "EEE", "VVV")
partial <- suppressWarnings(mclustICL(xb, G = 1:2, modelNames = "EII"))

one <- function() {
  list(
    faithful_G1to4_4models = suppressWarnings(
      mclustICL(xfa, G = 1:4, modelNames = c("EII", "VVV", "EEE", "VEV"))),
    oneD_default_G1to3 = suppressWarnings(mclustICL(x1, G = 1:3)),
    xb_G1to3_2models = suppressWarnings(mclustICL(xb, G = 1:3, modelNames = c("EII", "VVV"))),
    x3_G1to3_6models = suppressWarnings(mclustICL(x3, G = 1:3, modelNames = models6)),
    oneD_G1_E_x1to4 = suppressWarnings(mclustICL(c(1, 2, 3, 4), G = 1, modelNames = "E")),
    xb_with_x = suppressWarnings(mclustICL(xb, G = 1:3, modelNames = c("EII", "VVV"), x = partial))
  )
}

fits <- one()
fmt <- function(x) ifelse(is.na(x), "NA", sprintf("%.17g", as.numeric(x)))
lines <- character(0)
for (k in names(fits)) {
  b <- fits[[k]]
  lines <- c(lines,
    paste("CASE", k, sep = "\t"),
    paste(c(k, "values", dim(b)), collapse = "\t"),
    paste(c(k, "valuesdata", fmt(as.vector(unclass(b)))), collapse = "\t"),
    paste(c(k, "G", fmt(attr(b, "G"))), collapse = "\t"),
    paste(c(k, "returnCodes", fmt(as.vector(attr(b, "returnCodes")))), collapse = "\t"),
    paste(c(k, "n", fmt(attr(b, "n")), "d", fmt(attr(b, "d")),
            "oneD", fmt(as.numeric(attr(b, "oneD")))), collapse = "\t"),
    paste(c(k, "modelNames", attr(b, "modelNames")), collapse = "\t"),
    paste(c(k, "criterion", attr(b, "criterion"), class(b)), collapse = "\t")
  )
}

elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  invisible(one())
  elapsed[i] <- (as.numeric(Sys.time()) - t0) * 1000
}
lines <- c(lines, paste("time_ms", fmt(median(elapsed)), sep = "\t"))

dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)
writeLines(lines, file.path(out_dir, "mclustICL-r.txt"))
cat("R mclustICL all cases median ms:", median(elapsed), "\n")
