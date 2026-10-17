suppressPackageStartupMessages(library(statmod))
if (as.character(packageVersion("statmod")) != "1.5.2") stop("expected statmod 1.5.2")

one <- function() {
  set.seed(424242)
  c(
    rinvgauss(5, mean = 1, dispersion = 0.5),
    rinvgauss(3, mean = c(1, 2, 3), dispersion = 0.3),
    rinvgauss(2, mean = Inf, dispersion = 1),
    rinvgauss(2, mean = 1, dispersion = Inf),
    rinvgauss(2, mean = -1, dispersion = 1),
    rinvgauss(2, mean = 1, shape = 4),
    rinvgauss(c(1, 1, 1))
  )
}

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(paste(sprintf("%.17g", as.numeric(value)), collapse = ","), "\n", sep = "")
cat("MS\n")
cat(sprintf("%.17g\n", median(elapsed) * 1000))
