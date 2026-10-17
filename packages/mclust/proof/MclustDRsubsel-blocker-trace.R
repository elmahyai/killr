.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(mclust))
if (packageDescription("mclust")$Version != "6.1.3") stop("expected mclust 6.1.3")

# Records R's verbose trace of MclustDRsubsel on the proof fixture. The trace
# shows the cycles pick G = 2 and G = 3 fits, so the Python port needs the
# multi-component mclustBIC and Mclust path (blocked_by: Mclust).
proof_dir <- "/home/ahmed/killr_projects/killr/packages/mclust/proof"
source(file.path(proof_dir, "MclustDR-export.R"))
dr <- MclustDR(mod, lambda = 0.7)
old <- mclust.options("hcUse")
mclust.options(hcUse = "VARS")
on.exit(mclust.options(hcUse = old))
sub <- MclustDRsubsel(dr, G = 1:3, modelNames = c("VEI", "EEE"), verbose = TRUE)
print(sub$numdir)
print(sub$basisx)
