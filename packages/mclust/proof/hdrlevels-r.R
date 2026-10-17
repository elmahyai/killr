.libPaths(c(path.expand("~/R/x86_64-pc-linux-gnu-library/4.5"), .libPaths())); suppressPackageStartupMessages(library(mclust))
one<-function() hdrlevels(c(0.1,0.2,0.4,0.8,1.2),c(.5,.9,0))
value<-one();elapsed<-numeric(20);for(i in seq_len(20)){t0<-as.numeric(Sys.time());one();elapsed[i]<-as.numeric(Sys.time())-t0}
cat(sprintf("%.17g\n",value),sep="");cat(sprintf("%.17g\n",median(elapsed)*1000))
