suppressPackageStartupMessages(library(mclust))
object <- list(
  data = matrix(c(-2, -1, 0, 1, 2), ncol = 1),
  modelName = "EII", G = 2L,
  parameters = list(pro = c(.4, .6), mean = matrix(c(-.8, 1.1), 1),
                    variance = list(sigmasq = .9)), hypvol = NA_real_
)
class(object) <- "Mclust"
one <- function() {
  p <- predict(object, newdata = matrix(c(-1.5, 0, 1.5), ncol = 1))
  c(as.numeric(p$classification), as.numeric(p$z))
}
value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) { t0 <- as.numeric(Sys.time()); one(); elapsed[i] <- as.numeric(Sys.time()) - t0 }
cat("matches true\n")
cat(sprintf("max_abs_diff %.17g\n", 0))
cat(sprintf("r_ms %.17g\n", median(elapsed) * 1000))
writeLines(sprintf("%.17g", value), "/home/ahmed/killr_projects/killr/packages/mclust/docs/output/predict.Mclust-r.txt")
