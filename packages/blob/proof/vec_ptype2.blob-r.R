library(blob)
f <- function() length(vec_ptype2.blob(blob(raw(1)), blob(raw(2))))
cat(f(),"\n",sep="");f();t<-numeric(20)
for(i in seq_len(20)){a<-Sys.time();f();t[i]<-as.numeric(difftime(Sys.time(),a,units="secs"))*1000};cat(sprintf("r_ms=%.9f\n",median(t)))
