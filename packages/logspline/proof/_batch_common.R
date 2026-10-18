library(logspline)
fit <- list(coef.pol=c(-2, .1), coef.kts=c(.01, -.02),
            knots=c(-1, 1), bound=c(1, -2, 1, 2),
            samples=100, penalty=log(100),
            logl=matrix(c(3,2,-100, 4,2,-99), ncol=3, byrow=TRUE))
old <- list(coef=c(-2,.1,.01,-.02), knots=c(-1,1),
            bound=c(1,-2,1,2), sample=100, penalty=log(100),
            logl=c(-100,-99), delete=TRUE)
