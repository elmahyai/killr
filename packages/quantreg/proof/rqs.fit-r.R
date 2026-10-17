suppressPackageStartupMessages(library(quantreg))
d <- as.matrix(read.table("/home/ahmed/killr_projects/killr/packages/quantreg/quantreg/data/check_design.txt"))
X <- d[,1:3]
y <- d[,4]
Y <- cbind(y, 2 * y - X[,2], X[,2] + 0.3 * y)
one <- function() {
  a <- rqs.fit(X, Y, tau = 0.25)
  b <- rqs.fit(X, Y, tau = 0.75)
  c(as.vector(t(a)), as.vector(t(b)))
}
invisible(one())
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
value <- one()
cat(paste(sprintf("%.17g", as.numeric(value)), collapse=","), "\n")
cat(sprintf("%.17g\n", median(elapsed) * 1000))
