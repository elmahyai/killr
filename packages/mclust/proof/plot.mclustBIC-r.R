suppressPackageStartupMessages(library(mclust))
if (packageDescription("mclust")$Version != "6.1.3") stop("expected mclust 6.1.3")

# Scope: only G = 1 objects. The multi-component path of mclustBIC is verified
# by another owner.
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
models3 <- c("EII", "VVV", "EEE")
bic_a <- mclustBIC(X2, G = 1, modelNames = models6)
bic_b <- mclustBIC(X3, G = 1, modelNames = models3)
bic_c <- mclustBIC(X2, G = 1, modelNames = c("VVV", "EII"))

# Input check: the BIC values R computes for these objects. The Python side
# compares its own mclustBIC values with these.
write_matrix <- function(m, path) {
  lines <- apply(m, 1, function(r) paste(sprintf("%.17g", r), collapse = "\t"))
  writeLines(lines, path)
}
write_matrix(unclass(bic_a), file.path(proof_dir, "plot.mclustBIC_bic_a.txt"))
write_matrix(unclass(bic_b), file.path(proof_dir, "plot.mclustBIC_bic_b.txt"))
write_matrix(unclass(bic_c), file.path(proof_dir, "plot.mclustBIC_bic_c.txt"))
writeLines(c(paste(models6, collapse = " "), paste(models3, collapse = " "),
             "VVV EII"), file.path(proof_dir, "plot.mclustBIC_models.txt"))

cases <- list(
  six_models_d2 = bic_a,
  three_models_d3 = bic_b,
  subset_two_models_d2 = bic_c
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
  plot(obj)
  trace_stop()
  untrace("axis", where = asNamespace("graphics"))
  out <- c(out, paste0("CASE\t", nm), .LOG$out)
}
dev.off()
writeLines(out, file.path(out_dir, "plot.mclustBIC-r.txt"))

# Timing: the data computation of plot.mclustBIC, which is the symbols, the
# colours, the model columns, the y range and the x values. Drawing is not
# timed. The object is the six-model G = 1 fit.
symbols_all <- mclust.options("bicPlotSymbols")
colors_all <- mclust.options("bicPlotColors")
one <- function() {
  x <- unclass(bic_a)
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
  elapsed[i] <- as.numeric(Sys.time()) - t0
}
writeLines(sprintf("%.17g", median(elapsed) * 1000), file.path(out_dir, "plot.mclustBIC-r-time.txt"))
cat("ok\n")
