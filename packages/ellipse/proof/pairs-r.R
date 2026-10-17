x <- matrix(c(1,2,3,2,4,1,3,1,5,4,2,6), 6, 2)
one <- function() {
  png("/tmp/pairs-r.png", width=600, height=600)
  pairs(x)
  dev.off()
  c(range(x[,1]), range(x[,2]))
}
one(); tm <- numeric(20)
for (k in 1:20) { t0 <- Sys.time(); v <- one(); tm[k] <- as.numeric(difftime(Sys.time(),t0,units="secs"))*1000 }
writeLines(as.character(median(tm)), "/tmp/pairs-r-time.txt")
writeLines(paste(v, collapse=" "), "/tmp/pairs-r-values.txt")
