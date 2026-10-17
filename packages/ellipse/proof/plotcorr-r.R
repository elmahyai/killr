suppressPackageStartupMessages(library(ellipse, lib.loc = "/tmp/ellipse-lib"))
options(digits = 17)
corr <- matrix(c(1,.2,-.7,.2,1,.45,-.7,.45,1), 3, 3, byrow=TRUE)
one <- function() {
  out <- list()
  for (i in 1:3) for (j in 1:3) {
    mat <- diag(c(1, 1)); mat[1,2] <- mat[2,1] <- corr[i,j]
    z <- ellipse(mat, t=.43)
    z[,1] <- z[,1] + j; z[,2] <- z[,2] + 4-i
    out[[length(out)+1]] <- z
  }
  out
}
invisible(one())
tm <- numeric(20)
for (k in 1:20) { t0 <- Sys.time(); v <- one(); tm[k] <- as.numeric(difftime(Sys.time(),t0,units="secs"))*1000 }
write.table(do.call(rbind, v), "/tmp/plotcorr-r-values.txt", row.names=FALSE, col.names=FALSE)
cat("r_ms ", median(tm), "\n")
writeLines(as.character(median(tm)), "/tmp/plotcorr-r-time.txt")
