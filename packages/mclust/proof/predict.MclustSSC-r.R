suppressPackageStartupMessages(library(mclust))
proof <- "/home/ahmed/killr_projects/killr/packages/mclust/proof"
X <- as.matrix(read.csv(file.path(proof,"MclustSSC_X.csv")))
cl <- read.csv(file.path(proof,"MclustSSC_class.csv"))[[1L]]
one <- function() { m <- MclustSSC(X,cl,verbose=FALSE); p <- predict(m,X[1:6,,drop=FALSE]); c(p$z,as.integer(p$classification)) }
v <- one(); t <- numeric(20)
for(i in 1:20){s<-as.numeric(Sys.time());one();t[i]<-as.numeric(Sys.time())-s}
writeLines(sprintf("%.17g",v),file.path(proof,"predict.MclustSSC-r-values.txt"))
writeLines(sprintf("%.17g",median(t)*1000),file.path(proof,"predict.MclustSSC-r-ms.txt"))
