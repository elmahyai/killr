# Proof: R mclust 6.1.3 plot.mclustICL on objects from R's mclustICL. Run from packages/mclust:
#   Rscript proof/plot.mclustICL-r.R
# Writes docs/output/plot.mclustICL-r.txt. For each case the log holds the ICL object
# values (V icl_values, column-major), then the window, the lines and the axis ticks
# that plot.mclustICL draws, as trace() records them (plot_trace.R). The timed part
# is the data computation of plot.mclustBIC (no drawing), median of 20 calls, in
# docs/output/plot.mclustICL-r-time.txt.
suppressPackageStartupMessages(library(mclust))
if (packageDescription("mclust")$Version != "6.1.3") stop("expected mclust 6.1.3")
proof_dir <- "/home/ahmed/killr_projects/killr/packages/mclust/proof"
out_dir <- "/home/ahmed/killr_projects/killr/packages/mclust/docs/output"
source(file.path(proof_dir, "plot_trace.R"))
source(file.path(proof_dir, "plot_record.R"))  # make_fixtures

fx <- make_fixtures()
X3 <- fx$data3
X2 <- fx$data2
dimnames(X3) <- NULL
dimnames(X2) <- NULL

models6 <- c("EII", "VII", "EEI", "VVI", "EEE", "VVV")
icl1 <- suppressWarnings(mclustICL(X2, G = 1, modelNames = models6))
icl3 <- suppressWarnings(mclustICL(X2, G = 1:3, modelNames = models6))
icl3b <- suppressWarnings(mclustICL(X3, G = 1:3, modelNames = c("EEE", "VVV")))
icl23 <- suppressWarnings(mclustICL(X2, G = 2:3, modelNames = c("VVV", "EII")))

cases <- list(
  one_row_six_models = icl1,
  three_rows_six_models = icl3,
  three_rows_two_models_d3 = icl3b,
  two_rows_subset_two_models = icl23
)

out <- character(0)
pdf(NULL)
for (nm in names(cases)) {
  obj <- cases[[nm]]
  .LOG$out <- character(0)
  trace_start()
  trace("axis",
        tracer = quote(if (!is.null(at)) .add("V", paste0("axis", side), .fmtn(at))),
        where = asNamespace("graphics"), print = FALSE)
  .value("icl_values", as.vector(unclass(obj)))
  plot(obj)
  trace_stop()
  untrace("axis", where = asNamespace("graphics"))
  out <- c(out, paste0("CASE\t", nm), .LOG$out)
}
dev.off()
writeLines(out, file.path(out_dir, "plot.mclustICL-r.txt"))

# Timing: the data computation of plot.mclustBIC on the three-row object.
symbols_all <- mclust.options("bicPlotSymbols")
colors_all <- mclust.options("bicPlotColors")
one <- function() {
  x <- unclass(icl3)
  n <- ncol(x)
  dnx <- dimnames(x)
  x <- matrix(as.vector(x), ncol = n)
  dimnames(x) <- dnx
  modelNames <- dimnames(x)[[2]]
  sym <- symbols_all[modelNames]
  col <- colors_all[modelNames]
  x <- x[, modelNames, drop = FALSE]
  ylim <- range(as.vector(x[!is.na(x)]))
  G <- as.numeric(dnx[[1]])
  list(sym = sym, col = col, ylim = ylim, G = G)
}
invisible(one())
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  invisible(one())
  elapsed[i] <- (as.numeric(Sys.time()) - t0) * 1000
}
writeLines(sprintf("%.17g", median(elapsed)), file.path(out_dir, "plot.mclustICL-r-time.txt"))
cat("ok\n")
