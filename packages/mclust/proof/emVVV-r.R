suppressPackageStartupMessages(library(mclust))
if (packageDescription("mclust")$Version != "6.1.3") stop("expected mclust 6.1.3")
n<-60L;p<-3L;x<-matrix(0,n,p)
for(i in 1:n)for(j in 1:p)x[i,j]<-sin(.37*i+1.3*j)+.4*cos(.11*i*j)+.05*i/n*j
mu<-matrix(c(.1,-.2,.3,.5,.4,-.1),p,2)
U<-array(0,c(p,p,2));U[,,1]<-matrix(c(1.4,0,0,.2,1.1,0,.1,.3,.9),p,p);U[,,2]<-matrix(c(1.2,0,0,-.1,.8,0,.2,.15,1.1),p,p)
pars<-function(pro,Vinv=NULL){a<-list(pro=pro,mean=mu,variance=list(cholsigma=U));if(!is.null(Vinv))a$Vinv<-Vinv;a}
flat<-function(o){v<-o$parameters$variance;c(attr(o,"returnCode"),as.numeric(o$parameters$pro),as.numeric(o$parameters$mean),as.numeric(v$cholsigma),as.numeric(v$sigma),as.numeric(o$z))}
one<-function()c(flat(emVVV(x,pars(c(.4,.6)))),flat(emVVV(x,pars(c(.3,.45,.25),.15))))
value<-one();elapsed<-numeric(20)
for(i in seq_len(20)){t0<-as.numeric(Sys.time());one();elapsed[i]<-as.numeric(Sys.time())-t0}
cat(sprintf("%.17g\n",value),sep="");cat(sprintf("%.17g\n",median(elapsed)*1000))
