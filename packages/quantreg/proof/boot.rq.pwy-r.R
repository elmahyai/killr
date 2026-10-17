suppressPackageStartupMessages(library(quantreg))
d <- as.matrix(read.table("/home/ahmed/killr_projects/killr/packages/quantreg/quantreg/data/check_design.txt"))
X <- d[,1:3]; y <- d[,4]
# Fixed inputs, built once and not timed: 200 replicates of the weighted design t(X) %*% ((U < 0.5) - 0.5).
set.seed(1)
U <- matrix(runif(length(y) * 200), length(y), 200)
W <- as.matrix(t(X) %*% ((U < 0.5) - 0.5))
one <- function() as.numeric(quantreg:::boot.rq.pwy(W, X, y, tau=0.5))
invisible(one())
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time()); one(); elapsed[[i]] <- as.numeric(Sys.time())-t0
}
value <- one()
cat(paste(sprintf("%.17g", value), collapse=","), "\n")
cat(sprintf("%.17g\n", median(elapsed)*1000))
