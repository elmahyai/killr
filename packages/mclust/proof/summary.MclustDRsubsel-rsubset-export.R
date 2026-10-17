.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(mclust))
if (packageDescription("mclust")$Version != "6.1.3") stop("expected mclust 6.1.3")

# Exports R's own MclustDRsubsel output, so the Python summary can be checked
# against R's exact subset object without depending on the Python subset fit.
proof_dir <- "/home/ahmed/killr_projects/killr/packages/mclust/proof"
source(file.path(proof_dir, "MclustDR-export.R"))
dr <- MclustDR(mod, lambda = 0.7)
old <- mclust.options("hcUse")
mclust.options(hcUse = "VARS")
sub <- MclustDRsubsel(dr, G = 1:3, modelNames = c("VEI", "EEE"), verbose = FALSE)
mclust.options(hcUse = old)

write.csv(as.matrix(sub$basisx), file.path(proof_dir, "summary.MclustDRsubsel_R_basisx.csv"), row.names = FALSE)
write.csv(as.matrix(sub$std.basisx), file.path(proof_dir, "summary.MclustDRsubsel_R_std_basisx.csv"), row.names = FALSE)
write.csv(as.matrix(sub$classification), file.path(proof_dir, "summary.MclustDRsubsel_R_classification.csv"), row.names = FALSE)
writeLines(sprintf("%.17g", as.numeric(sub$evalues)), file.path(proof_dir, "summary.MclustDRsubsel_R_evalues.txt"))
writeLines(
  c(sub$type, as.character(sub$modelName), as.character(sub$G), as.character(sub$numdir), sprintf("%.17g", sub$lambda)),
  file.path(proof_dir, "summary.MclustDRsubsel_R_meta.txt")
)
