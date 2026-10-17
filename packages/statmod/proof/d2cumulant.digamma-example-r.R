suppressPackageStartupMessages(library(statmod))
if (as.character(packageVersion("statmod")) != "1.5.2") stop("expected statmod 1.5.2")
theta <- c(-1, -0.5, -0.1)
print(d2cumulant.digamma(theta))
