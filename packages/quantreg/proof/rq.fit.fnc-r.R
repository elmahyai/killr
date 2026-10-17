suppressPackageStartupMessages(library(quantreg))
d <- as.matrix(read.table("/home/ahmed/killr_projects/killr/packages/quantreg/quantreg/data/check_design.txt"))
X <- d[,1:3]
y <- d[,4]
one <- function() {
  f <- rq.fit.fnc(X, y, matrix(c(0,1,0),1,3), 0, tau=0.5)
  c(f$coef, f$resid, f$it)
}
one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
 t0 <- as.numeric(Sys.time()); one(); elapsed[[i]] <- as.numeric(Sys.time())-t0
}
value <- one()
cat(paste(sprintf('%.17g', as.numeric(value)), collapse=','), '\n')
cat(sprintf('%.17g\n', median(elapsed)*1000))
