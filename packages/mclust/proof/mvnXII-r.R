suppressPackageStartupMessages(library(mclust))
out <- "/home/ahmed/killr_projects/killr/packages/mclust/docs/output/mvnXII-r.txt"
cases <- list(
  nonsingular = matrix(c(-1.2,0.5,2.1,1.7,-0.3,0.9,3.2,1.1,0.4,-0.8,1.3,2.6,2.2,1.5,-1.1,0.7,1.1,-1.7,0.2,3.4,3.3,0.2,2.4,-0.5), ncol=4, byrow=TRUE),
  singular = matrix(rep(c(1, 2, 3, 4), 3), ncol=4, byrow=TRUE)
)
one <- function() invisible(lapply(cases, mvnXII))
lines <- character(0)
for (nm in names(cases)) {
  y <- mvnXII(cases[[nm]])
  value <- c(y$parameters$mean, y$parameters$variance$sigmasq, y$loglik)
  lines <- c(lines, paste("CASE", nm), sprintf("%.17g", value))
}
invisible(one())
elapsed <- numeric(20)
for (i in seq_len(20)) { t0 <- as.numeric(Sys.time()); one(); elapsed[i] <- as.numeric(Sys.time()) - t0 }
lines <- c(lines, sprintf("r_ms %.17g", median(elapsed)*1000))
writeLines(lines, out)
cat(paste(lines, collapse="\n"), "\n", sep="")
