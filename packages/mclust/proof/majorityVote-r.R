.libPaths(c(path.expand("~/R/x86_64-pc-linux-gnu-library/4.5"), .libPaths())); suppressPackageStartupMessages(library(mclust))
one<-function(){o<-majorityVote(c("a","b","a","c","a"));c(o$ind,o$majority,o$table)}
value<-one();elapsed<-numeric(20);for(i in seq_len(20)){t0<-as.numeric(Sys.time());one();elapsed[i]<-as.numeric(Sys.time())-t0}
cat(value,sep="\n");cat(sprintf("%.17g\n",median(elapsed)*1000))
