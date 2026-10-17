suppressPackageStartupMessages(library(quantreg))
d <- as.matrix(read.table("/home/ahmed/killr_projects/killr/packages/quantreg/quantreg/data/check_design.txt"))
X <- d[,1:3]; y <- d[,4]
# rq.fit.pfnb returns the coefficient as the negated dual, so the dual is -coefficients.
one <- function() {
  set.seed(1)
  f <- rq.fit.pfnb(X, y, tau=0.5)
  c(as.numeric(f$coefficients), -as.numeric(f$coefficients), as.numeric(f$nit), as.numeric(f$flag))
}
invisible(one())
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time()); one(); elapsed[[i]] <- as.numeric(Sys.time())-t0
}
value <- one()
cat(paste(sprintf("%.17g", as.numeric(value)), collapse=","), "\n")
cat(sprintf("%.17g\n", median(elapsed)*1000))
