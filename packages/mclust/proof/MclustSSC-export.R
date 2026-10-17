.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(mclust))
if (packageDescription("mclust")$Version != "6.1.3") stop("expected mclust 6.1.3")

proof <- "/home/ahmed/killr_projects/killr/packages/mclust/proof"

n <- 200L
pars <- list(
  pro = c(0.5, 0.5),
  mean = matrix(c(-1, 1), nrow = 2, ncol = 2, byrow = TRUE),
  variance = mclustVariance("EII", d = 2, G = 2)
)
pars$variance$sigmasq <- 1
data <- sim("EII", parameters = pars, n = n, seed = 12L)
class <- data[, 1L]
X <- data[, -1, drop = FALSE]
cl <- class
set.seed(42L)
cl[sample(1L:n, size = 195L)] <- NA

write.csv(X, file.path(proof, "MclustSSC_X.csv"), row.names = FALSE)
write.csv(
  data.frame(class = cl),
  file.path(proof, "MclustSSC_class.csv"),
  row.names = FALSE
)

mod <- MclustSSC(X, cl, verbose = FALSE)

writeLines(mod$modelName, file.path(proof, "MclustSSC_modelName.txt"))
writeLines(as.character(mod$G), file.path(proof, "MclustSSC_G.txt"))
write.csv(mod$BIC, file.path(proof, "MclustSSC_BIC.csv"), row.names = TRUE)
writeLines(sprintf("%.17g", mod$loglik), file.path(proof, "MclustSSC_loglik.txt"))
writeLines(sprintf("%.17g", mod$df), file.path(proof, "MclustSSC_df.txt"))
writeLines(sprintf("%.17g", mod$bic), file.path(proof, "MclustSSC_bic.txt"))
write.csv(mod$z, file.path(proof, "MclustSSC_z.csv"), row.names = FALSE)
write.csv(
  data.frame(classification = as.character(mod$classification)),
  file.path(proof, "MclustSSC_classification.csv"),
  row.names = FALSE
)
write.csv(mod$parameters$pro, file.path(proof, "MclustSSC_pro.csv"), row.names = FALSE)
write.csv(mod$parameters$mean, file.path(proof, "MclustSSC_mean.csv"), row.names = FALSE)
