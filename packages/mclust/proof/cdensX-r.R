suppressPackageStartupMessages(library(mclust))
if (packageDescription("mclust")$Version != "6.1.3") stop("expected mclust 6.1.3")
proof_dir <- "/home/ahmed/killr_projects/killr/packages/mclust/proof"
output_dir <- "/home/ahmed/killr_projects/killr/packages/mclust/docs/output"
n <- 40L; p <- 3L; G <- 3L
x <- matrix(0, n, p)
for (i in 1:n) for (j in 1:p) x[i, j] <- ((i * 7 + j * 13) %% 17) / 17 - 0.5 + 0.05 * i * j / n
xv <- x[, 1]
parameters <- list(mean = c(-0.4, 0.1, 0.6), variance = list(modelName = "X", sigmasq = 0.9))
one <- function() cdensX(xv, logarithm = FALSE, parameters = parameters)
value <- one()
s <- matrix(sprintf("%.17g", value), nrow(value))
writeLines(apply(s, 1, paste, collapse = " "), file.path(output_dir, "cdensX-r.txt"))
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[i] <- as.numeric(Sys.time()) - t0
}
writeLines(sprintf("%.17g", median(elapsed) * 1000), file.path(proof_dir, "cdensX-r-ms.txt"))
