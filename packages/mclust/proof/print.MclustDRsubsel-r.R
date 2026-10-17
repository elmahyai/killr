suppressPackageStartupMessages(library(mclust))
if (packageDescription("mclust")$Version != "6.1.3") stop("expected mclust 6.1.3")
proof_dir <- "/home/ahmed/killr_projects/killr/packages/mclust/proof"
source(file.path(proof_dir, "MclustDR-export.R"))
dr <- MclustDR(mod, lambda = 0.7)

# the subset-selection fit is made outside the timed call, with hcUse = "VARS"
old <- mclust.options("hcUse")
mclust.options(hcUse = "VARS")
sub <- MclustDRsubsel(dr, G = 1:3, modelNames = c("VEI", "EEE"), verbose = FALSE)
mclust.options(hcUse = old)
one <- function() capture.output(print(sub))

# untimed call: printed text
value <- one()
writeLines(value, file.path(proof_dir, "../docs/output/print.MclustDRsubsel-r.txt"))

# timed: median of 20 calls of print() alone
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[i] <- as.numeric(Sys.time()) - t0
}
cat(sprintf("r_ms %.17g\n", median(elapsed) * 1000))
