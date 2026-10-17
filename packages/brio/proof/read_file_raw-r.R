library(brio)
f<-tempfile();writeBin(as.raw(c(0,1,255,10)),f);one<-function() read_file_raw(f);value<-one();times<-numeric(20)
for(i in seq_len(20)){t<-Sys.time();one();times[i]<-as.numeric(difftime(Sys.time(),t,units="secs"))*1000}
cat(sprintf('{"value":"%s","median_ms":%.9f}\n',paste(as.integer(value),collapse=","),median(times)));unlink(f)
