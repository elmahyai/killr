suppressPackageStartupMessages(library(mclust))
if (packageDescription("mclust")$Version != "6.1.3") stop("expected mclust 6.1.3")
x <- matrix(c(-1.2,0.5,2.1,1.7,-0.3,0.9,3.2,1.1,0.4,-0.8,1.3,2.6,2.2,1.5,-1.1,0.7,1.1,-1.7,0.2,3.4,3.3,0.2,2.4,-0.5), ncol=4, byrow=TRUE)
one <- function() { y <- emXII(x); c(y$parameters$mean, y$parameters$variance$sigmasq, as.vector(y$parameters$variance$Sigma), y$loglik) }
value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) { t0 <- as.numeric(Sys.time()); one(); elapsed[i] <- as.numeric(Sys.time()) - t0 }
cat(sprintf("%.17g\n", value), sep = "")
cat(sprintf("%.17g\n", median(elapsed) * 1000))
