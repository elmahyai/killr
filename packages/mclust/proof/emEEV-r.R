suppressPackageStartupMessages(library(mclust))
if (packageDescription("mclust")$Version != "6.1.3") stop("expected mclust 6.1.3")
n <- 60L; p <- 3L
x <- matrix(0,n,p)
for(i in 1:n) for(j in 1:p) x[i,j] <- sin(.37*i+1.3*j)+.4*cos(.11*i*j)+.05*i/n*j
mu <- matrix(c(.1,-.2,.3,.5,.4,-.1),p,2)
a <- pi/6; b <- pi/5
Rz <- matrix(c(cos(a),sin(a),0,-sin(a),cos(a),0,0,0,1),3,3)
Rx <- matrix(c(1,0,0,0,cos(b),sin(b),0,-sin(b),cos(b)),3,3)
O <- Rz %*% Rx; O3 <- array(rep(as.numeric(O),2),c(p,p,2)); shape <- matrix(c(1.5,.6,.9,.8,1.4,1.1),p,2)
pars <- function(pro,Vinv=NULL) { a <- list(pro=pro,mean=mu,variance=list(scale=.9,shape=shape,orientation=O3)); if(!is.null(Vinv)) a$Vinv<-Vinv; a }
flat <- function(o) { v<-o$parameters$variance; c(attr(o,"returnCode"),as.numeric(o$parameters$pro),as.numeric(o$parameters$mean),v$scale,as.numeric(v$shape),as.numeric(v$orientation),as.numeric(v$sigma),as.numeric(o$z)) }
one <- function() c(flat(emEEV(x,pars(c(.4,.6)))),flat(emEEV(x,pars(c(.3,.45,.25),.15))))
value<-one(); elapsed<-numeric(20)
for(i in seq_len(20)){t0<-as.numeric(Sys.time());one();elapsed[i]<-as.numeric(Sys.time())-t0}
cat(sprintf("%.17g\n",value),sep="");cat(sprintf("%.17g\n",median(elapsed)*1000))
