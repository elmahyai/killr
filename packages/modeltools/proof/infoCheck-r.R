library(modeltools)
measure <- function(FUN) { value <- FUN(); times <- numeric(20); for(i in seq_len(20)){t<-Sys.time();FUN();times[i]<-as.numeric(difftime(Sys.time(),t,units='secs'))*1000}; cat('value=',paste(value,collapse=','),'\n',sep='');cat('r_ms=',median(times),'\n',sep='') }
measure(function() { setClass('foo', representation(x='numeric')); setMethod('info', signature(object='foo',which='character'), function(object,which,...) c('help')); infoCheck(new('foo',x=1),'help') })
