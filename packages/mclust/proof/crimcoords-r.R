suppressPackageStartupMessages(library(mclust))
proof <- "/home/ahmed/killr_projects/killr/packages/mclust/proof"
X <- matrix(c(1,2,3, 2,1,4, 4,3,2, 5,4,1, 6,2,3, 7,5,2), 6, 3, byrow=TRUE)
cl <- c("a","a","b","b","c","c")
one <- function() { z <- crimcoords(X, cl); c(z$means,z$B,z$W,z$evalues,z$basis,z$projection) }
v <- one(); t <- numeric(20)
for (i in 1:20) { s <- as.numeric(Sys.time()); one(); t[i] <- as.numeric(Sys.time())-s }
writeLines(sprintf("%.17g", v), file.path(proof,"crimcoords-r-values.txt"))
writeLines(sprintf("%.17g", median(t)*1000), file.path(proof,"crimcoords-r-ms.txt"))
