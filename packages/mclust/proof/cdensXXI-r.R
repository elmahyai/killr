suppressPackageStartupMessages(library(mclust))
if (packageDescription("mclust")$Version != "6.1.3") stop("expected mclust 6.1.3")
proof_dir <- "/home/ahmed/killr_projects/killr/packages/mclust/proof"
output_dir <- "/home/ahmed/killr_projects/killr/packages/mclust/docs/output"
n <- 40L; p <- 3L; G <- 3L
x <- matrix(0, n, p)
for (i in 1:n) for (j in 1:p) x[i, j] <- ((i * 7 + j * 13) %% 17) / 17 - 0.5 + 0.05 * i * j / n
mu <- matrix(0, p, G)
for (j in 1:p) for (k in 1:G) mu[j, k] <- 0.3 * k - 0.2 * j + 0.1 * j * k
parameters <- list(mean = mu,
                   variance = list(modelName = "XXI", scale = 1.2, shape = c(0.7, 1.1, 1.9)))
one <- function() cdensXXI(x, logarithm = FALSE, parameters = parameters)
value <- one()
s <- matrix(sprintf("%.17g", value), nrow(value))
writeLines(apply(s, 1, paste, collapse = " "), file.path(output_dir, "cdensXXI-r.txt"))
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[i] <- as.numeric(Sys.time()) - t0
}
writeLines(sprintf("%.17g", median(elapsed) * 1000), file.path(proof_dir, "cdensXXI-r-ms.txt"))
