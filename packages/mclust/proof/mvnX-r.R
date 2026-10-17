suppressPackageStartupMessages(library(mclust))
x <- c(-1.2, 0.5, 2.1, 1.7, -0.3, 0.9, 3.2, 1.1)
one <- function() { y <- mvnX(x); c(y$parameters$mean, y$parameters$variance$sigmasq, y$loglik) }
value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) { t0 <- as.numeric(Sys.time()); one(); elapsed[i] <- as.numeric(Sys.time()) - t0 }
cat(sprintf("%.17g\n", value), sep = "")
cat(sprintf("%.17g\n", median(elapsed) * 1000))
