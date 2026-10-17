library(blob)
f <- function() new_blob(list(charToRaw("abc"), NULL))
v<-f(); cat(paste(paste(as.integer(v[[1]]),collapse=","),"NA",sep=";"),"\n",sep=""); f(); t<-numeric(20)
for(i in seq_len(20)){a<-Sys.time();f();t[i]<-as.numeric(difftime(Sys.time(),a,units="secs"))*1000};cat(sprintf("r_ms=%.9f\n",median(t)))
