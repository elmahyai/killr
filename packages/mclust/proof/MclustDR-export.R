suppressPackageStartupMessages(library(mclust))
if (packageDescription("mclust")$Version != "6.1.3") stop("expected mclust 6.1.3")
data(banknote, package = "mclust")
set.seed(12345)
mod <- Mclust(banknote[, c("Length", "Left", "Right", "Bottom")], G = 3, modelNames = "VEI")
dir <- "/home/ahmed/killr_projects/killr/packages/mclust/proof"
write.csv(as.matrix(mod$data), file.path(dir, "MclustDR_data.csv"), row.names = FALSE)
write.csv(mod$classification, file.path(dir, "MclustDR_classification.csv"), row.names = FALSE)
write.csv(mod$parameters$pro, file.path(dir, "MclustDR_pro.csv"), row.names = FALSE)
write.csv(mod$parameters$mean, file.path(dir, "MclustDR_mean.csv"), row.names = FALSE)
for (g in seq_len(mod$G)) {
  write.csv(mod$parameters$variance$sigma[, , g], file.path(dir, sprintf("MclustDR_sigma_%d.csv", g)), row.names = FALSE)
}
writeLines(
  c(as.character(mod$G), mod$modelName, as.character(mod$hypvol)),
  file.path(dir, "MclustDR_meta.txt")
)
