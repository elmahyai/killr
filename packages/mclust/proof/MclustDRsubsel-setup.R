.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(mclust))
if (packageDescription("mclust")$Version != "6.1.3") stop("expected mclust 6.1.3")

# Shared end-to-end input for MclustDRsubsel and summary.MclustDRsubsel:
# banknote (4 variables) -> Mclust(G = 3, VEI) -> MclustDR(lambda = 0.7).
# Python builds the same chain from the CSV written here.
proof_dir <- "/home/ahmed/killr_projects/killr/packages/mclust/proof"
data(banknote, package = "mclust")
x4 <- banknote[, c("Length", "Left", "Right", "Bottom")]
write.csv(x4, file.path(proof_dir, "MclustDRsubsel_banknote4.csv"), row.names = FALSE)
set.seed(12345)
mod <- Mclust(x4, G = 3, modelNames = "VEI")
dr <- MclustDR(mod, lambda = 0.7)

# Two cases. A: a small search. B: the default G = 1:9 and all default models.
cases <- list(
  A = function(...) MclustDRsubsel(dr, G = 1:3, modelNames = c("VEI", "EEE"), verbose = FALSE),
  B = function(...) MclustDRsubsel(dr, verbose = FALSE)
)
