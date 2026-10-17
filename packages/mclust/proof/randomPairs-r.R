.libPaths(c(path.expand("~/R/x86_64-pc-linux-gnu-library/4.5"), .libPaths())); suppressPackageStartupMessages(library(mclust))
one<-function(){p<-randomPairs(matrix(1:2,2,1),seed=7);c(dim(p),sum(p))}
value<-one();elapsed<-numeric(20);for(i in seq_len(20)){t0<-as.numeric(Sys.time());one();elapsed[i]<-as.numeric(Sys.time())-t0}
cat(sprintf("%.17g\n",value),sep="");cat(sprintf("%.17g\n",median(elapsed)*1000))
