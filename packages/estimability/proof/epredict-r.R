library(estimability)
X <- rbind(c(1,0,1,1), c(1,1,2,3), c(1,2,3,5))
L <- rbind(c(1,2,3,5), c(0,1,-1,0))
z <- svd(X, nu=0, nv=ncol(X))
run <- function() list(
  all_estble=is.estble(c(1,2), all.estble),
  basis=nonest.basis(X), svd_basis=nonest.basis.svd(z),
  legacy=legacy.nonest.basis(X),
  estimable=is.estble(L, nonest.basis(X)),
  subspace=estble.subspace(L, nonest.basis(X)),
  epredict=epredict(lm(y ~ x + z,
    data=data.frame(y=1:3, x=0:2, z=0:2)),
    newdata=data.frame(x=0:2, z=0:2), type="estimability"),
  eupdate=nonest.basis(lm(y ~ x + z,
    data=data.frame(y=1:3, x=0:2, z=0:2))))
run()
t <- numeric(20)
for (i in seq_len(20)) { a <- Sys.time(); run(); t[i] <- as.numeric(Sys.time()-a, units="secs")*1000 }
cat("median_ms=", median(t), "\n", sep="")
