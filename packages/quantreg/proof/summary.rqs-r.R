suppressPackageStartupMessages(library(quantreg))
d <- as.matrix(read.table("/home/ahmed/killr_projects/killr/packages/quantreg/quantreg/data/check_design.txt"))
df <- data.frame(y=d[,4], x1=d[,2], x2=d[,3])
fit <- rq(y ~ x1 + x2, data=df, tau=c(0.25,0.5,0.75))
one <- function() {
s <- summary(fit, se='nid'); s[[1]]$coef[,2]
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
