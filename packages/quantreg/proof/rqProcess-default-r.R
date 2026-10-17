suppressPackageStartupMessages(library(quantreg))
d <- as.matrix(read.table("/home/ahmed/killr_projects/killr/packages/quantreg/quantreg/data/check_design.txt"))
X <- d[,1:3]
y <- d[,4]
df <- data.frame(y = y, x1 = X[,2], x2 = X[,3])
taus <- 1:99/100
one <- function() {
  a <- rqProcess(y ~ x1 + x2, data = df, taus = taus, nullH = "location")
  b <- rqProcess(y ~ x1 + x2, data = df, taus = taus, nullH = "location-scale")
  c(a$qtaus, as.vector(a$Vhat), as.vector(a$vhat), a$n,
    b$qtaus, as.vector(b$Vhat), as.vector(b$vhat), b$n)
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
