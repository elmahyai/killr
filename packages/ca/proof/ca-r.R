dir.create("packages/ca/docs/output", recursive = TRUE, showWarnings = FALSE)
suppressPackageStartupMessages(library(ca))
write_vals <- function(name, x) {
  x <- as.numeric(x)
  write.table(x, file = paste0("packages/ca/docs/output/", name, "-r-values.csv"),
              row.names = FALSE, col.names = FALSE, sep = ",")
}
tab <- matrix(c(12, 5, 3, 4, 11, 6, 2, 7, 13, 8, 4, 9), 4, 3, byrow=TRUE)
f <- function() ca(tab)
t <- numeric(20); f()
for (i in 1:20) { a <- Sys.time(); f(); t[i] <- as.numeric(Sys.time()-a)*1000 }
z <- f()
write_vals("ca", c(z$sv, z$rowmass, z$colmass, z$rowcoord, z$colcoord))
write.table(median(t), "packages/ca/docs/output/ca-r-ms.txt", row.names=FALSE, col.names=FALSE)
write_vals("cacoord", c(cacoord(z, "principal")$rows, cacoord(z, "principal")$columns))
write_vals("caconv", c(caconv(tab, "freq", "ind"), caconv(tab, "freq", "Burt")))
dat <- data.frame(a=factor(c("x","y","x","z","y")), b=factor(c("u","u","v","v","u")))
m <- mjca(dat, lambda="indicator")
write_vals("mjca", c(m$sv, m$rowcoord, m$colcoord))
b <- caconv(dat, "rpm", "Burt")
it <- iterate.mjca(b, c(3,2), nd=2)
write_vals("iterate_mjca", c(it[[1]], it$crit))
timed <- function(name, f) {
  f()
  t <- numeric(20)
  for (i in 1:20) { a <- Sys.time(); f(); t[i] <- as.numeric(Sys.time()-a)*1000 }
  write.table(median(t), paste0("packages/ca/docs/output/", name, "-r-ms.txt"),
              row.names=FALSE, col.names=FALSE)
}
timed("cacoord", function() cacoord(z, "principal"))
timed("caconv", function() caconv(tab, "freq", "ind"))
timed("mjca", function() mjca(dat, lambda="indicator"))
timed("iterate_mjca", function() iterate.mjca(b, c(3,2), nd=2))
