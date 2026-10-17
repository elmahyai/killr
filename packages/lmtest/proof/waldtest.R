.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(lmtest))
x <- c(1,3,2,6,5,8,7,4,9,10,12,11,15,13,14,18,16,19,17,20)
y <- c(2,2,4,3,7,6,9,8,5,11,10,14,12,16,15,13,19,17,20,18)
z <- sqrt(x)
one <- function() {
w <- waldtest(lm(y ~ x))
paste(sprintf("%.17g", c(w[1,1], w[2,1], w[2,2], w[2,3], w[2,4])), collapse=",")
}

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
shown <- enc2utf8(paste(as.character(value), collapse = "|"))
shown <- gsub("\n", " / ", shown, fixed = TRUE)
cat("VALUE ", shown, "\n", sep = "")
cat(sprintf("MS %.17g\n", median(elapsed) * 1000))
