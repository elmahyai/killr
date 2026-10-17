suppressPackageStartupMessages(library(statmod))
if (as.character(packageVersion("statmod")) != "1.5.2") stop("expected statmod 1.5.2")
mu <- c(0.5, 1, 2)
print(canonic.digamma(mu))
