library(viridisLite)
options(digits = 17)
fs <- c('cividis','inferno','magma','mako','plasma','rocket','turbo','viridis')
for (f in fs) {
 fn <- get(f); fn(1)
 t <- numeric(20); for (i in 1:20) {a<-Sys.time(); z<-fn(1); t[i]<-as.numeric(Sys.time()-a,units='secs')*1000}
 cat(f,'|',paste(z,collapse=','),'|',median(t),'\n')
}
a<-Sys.time(); z<-viridisMap(1); unt<-as.numeric(Sys.time()-a,units='secs')*1000;t<-numeric(20);for(i in 1:20){a<-Sys.time();z<-viridisMap(1);t[i]<-as.numeric(Sys.time()-a,units='secs')*1000};cat('viridisMap','|',paste(sprintf('%.17g',c(z$R,z$G,z$B,z$alpha)),collapse=','),'|',median(t),'\n')
