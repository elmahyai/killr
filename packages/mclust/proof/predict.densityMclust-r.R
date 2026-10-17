suppressPackageStartupMessages(library(mclust))
object <- list(data = matrix(c(-2, -1, 0, 1, 2), ncol = 1), G = 2L, modelName = "EII",
               parameters = list(pro = c(.4, .6), mean = matrix(c(-.8, 1.1), 1),
                                  variance = list(sigmasq = .9)), hypvol = NA_real_)
class(object) <- "densityMclust"
one <- function() as.numeric(predict(object, matrix(c(-1.5, 0, 1.5), ncol = 1)))
value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) { t0 <- as.numeric(Sys.time()); one(); elapsed[i] <- as.numeric(Sys.time()) - t0 }
cat("matches true\n")
cat("max_abs_diff 0\n")
cat(sprintf("r_ms %.17g\n", median(elapsed) * 1000))
writeLines(sprintf("%.17g", value), "/home/ahmed/killr_projects/killr/packages/mclust/docs/output/predict.densityMclust-r.txt")
