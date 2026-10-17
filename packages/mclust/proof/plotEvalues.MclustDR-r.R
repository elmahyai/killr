suppressPackageStartupMessages(library(mclust))
if (packageDescription("mclust")$Version != "6.1.3") stop("expected mclust 6.1.3")
proof_dir <- "/home/ahmed/killr_projects/killr/packages/mclust/proof"
source(file.path(proof_dir, "plot_trace.R"))
source(file.path(proof_dir, "MclustDR-export.R"))
dr <- MclustDR(mod, lambda = 0.7)

out <- character(0)
pdf(NULL)

# Case 1: plot = TRUE. The drawing and the returned list.
trace_start()
res <- plotEvalues.MclustDR(dr, plot = TRUE)
trace_stop()
.value("dim", res$dim); .value("evalues", res$evalues)
.value("mean.contrib", res$mean.contrib); .value("var.contrib", res$var.contrib)
out <- c(out, "#CASE\tplot_true", .LOG$out)

# Case 2: plot = FALSE, numdir given. Only the returned list.
trace_start()
res2 <- plotEvalues.MclustDR(dr, numdir = 2, plot = FALSE)
trace_stop()
.value("dim", res2$dim); .value("evalues", res2$evalues)
.value("mean.contrib", res2$mean.contrib); .value("var.contrib", res2$var.contrib)
out <- c(out, "#CASE\tplot_false_numdir2", .LOG$out)
dev.off()
writeLines(out, file.path(proof_dir, "plotEvalues.MclustDR-r-log.txt"))

# Timing: the data computation only (plot = FALSE, no drawing).
one <- function() plotEvalues.MclustDR(dr, plot = FALSE)
value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[i] <- as.numeric(Sys.time()) - t0
}
writeLines(sprintf("%.17g", median(elapsed) * 1000), file.path(proof_dir, "plotEvalues.MclustDR-r-ms.txt"))
cat("ok\n")
