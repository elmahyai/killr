suppressPackageStartupMessages(library(quantreg))
if (as.character(packageVersion("quantreg")) != "6.1") stop("expected quantreg 6.1")
d <- as.matrix(read.table("/home/ahmed/killr_projects/killr/packages/quantreg/quantreg/data/check_design.txt"))
X <- d[, 1:3]
y <- d[, 4]
df <- data.frame(y = y, x1 = X[, 2], x2 = X[, 3])
fit <- rq(y ~ x1 + x2, tau = -1, data = df)
newdata <- data.frame(x1 = c(-1.5, -0.5, 0, 0.5, 1.5, 2.2), x2 = c(0.3, -1, 0.8, 0, -0.4, 1.1))
one <- function() predict(fit, newdata = newdata)
invisible(one())
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
value <- one()
cat(paste(sprintf("%.17g", as.numeric(value)), collapse = ","), "\n")
cat(sprintf("%.17g\n", median(elapsed) * 1000))
