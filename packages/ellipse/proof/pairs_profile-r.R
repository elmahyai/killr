library(ellipse, lib.loc = "/tmp/ellipse-lib")
tau <- seq(-1, 1, length.out=5)
make <- function(k) list(tau, cbind(tau + k, tau^2 + k))
x <- list(make(0), make(1))
class(x) <- "profile"
one <- function() {
  png("/tmp/pairs-profile-r.png", width=800, height=800)
  ellipse:::pairs_profile(x, plot.ellipse=FALSE)
  dev.off()
  c(range(unlist(lapply(x, `[[`, 1))), length(x) + 1)
}
one(); tm <- numeric(20)
for (k in 1:20) { t0 <- Sys.time(); v <- one(); tm[k] <- as.numeric(difftime(Sys.time(),t0,units="secs"))*1000 }
writeLines(as.character(median(tm)), "/tmp/pairs-profile-r-time.txt")
writeLines(paste(v, collapse=" "), "/tmp/pairs-profile-r-values.txt")
