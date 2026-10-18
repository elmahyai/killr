source("packages/logspline/proof/_batch_common.R")
print(.C("rpqlsd", as.double(c(fit$coef.pol,fit$coef.kts)),
         as.double(fit$knots), as.double(fit$bound), as.integer(0),
         pq=as.double(c(.1,.5,.9)), as.integer(2), as.integer(3),
         PACKAGE="logspline")$pq)
