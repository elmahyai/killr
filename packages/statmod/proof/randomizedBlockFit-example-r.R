suppressPackageStartupMessages(library(statmod))
if (as.character(packageVersion("statmod")) != "1.5.2") stop("expected statmod 1.5.2")
suppressPackageStartupMessages(library(MASS))
data(petrol)
mf <- model.frame(Y ~ SG + VP + V10 + EP, data = petrol)
mt <- attr(mf, "terms")
y <- model.response(mf, "numeric")
X <- model.matrix(mt, mf)
random <- petrol$No
lev <- unique.default(random)
Z <- 0 + (matrix(random, length(random), length(lev)) ==
  t(matrix(lev, length(lev), length(random))))
out <- randomizedBlockFit(y, X, Z)
print(cbind(varcomp = out$varcomp, se = out$se.varcomp))
