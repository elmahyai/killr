suppressPackageStartupMessages(library(quantreg))
xyz <- cbind(c(0, 1, 2, 4), c(2, 3, 1, 5))
object <- structure(list(xyz = xyz), class = "qss1")
newdata <- matrix(c(0, .25, 1, 1.5, 3, 4), ncol = 1)
one <- function() predict.qss1(object, newdata)
invisible(one())
elapsed <- numeric(20)
for (k in seq_len(20)) {
    t0 <- as.numeric(Sys.time())
    one()
    elapsed[[k]] <- as.numeric(Sys.time()) - t0
}
value <- one()
cat(paste(sprintf("%.17g", c(value$x, value$y, as.vector(t(as.matrix(value$D))))),
          collapse=","), "\n")
cat(sprintf("%.17g\n", median(elapsed) * 1000))
