suppressPackageStartupMessages(library(mclust))
if (packageDescription("mclust")$Version != "6.1.3") stop("expected mclust 6.1.3")
proof_dir <- "/home/ahmed/killr_projects/killr/packages/mclust/proof"
source(file.path(proof_dir, "MclustDR-export.R"))
dr <- MclustDR(mod, lambda = 0.7)
one <- function() summary(dr)

# untimed call: numeric values and printed text
s <- one()
values <- c(as.numeric(s$n), s$G, as.numeric(s$basis), as.numeric(s$std.basis),
            as.numeric(s$evalues), as.numeric(s$evalues.cumperc))
writeLines(sprintf("%.17g", values), file.path(proof_dir, "summary.MclustDR-r-values.txt"))
writeLines(capture.output(print(s)), file.path(proof_dir, "../docs/output/summary.MclustDR-r.txt"))

# timed: median of 20 calls of summary() alone
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[i] <- as.numeric(Sys.time()) - t0
}
cat(sprintf("r_ms %.17g\n", median(elapsed) * 1000))
