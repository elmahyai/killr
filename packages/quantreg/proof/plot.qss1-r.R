suppressPackageStartupMessages(library(quantreg))
xyz <- cbind(c(0, 1, 2, 4), c(2, 3, 1, 5))
object <- structure(xyz, class = "qss1")
one <- function() {
    c(object[, 1], object[, 2])
}
pdf(NULL)
invisible(one())
elapsed <- numeric(20)
for (k in seq_len(20)) {
    t0 <- as.numeric(Sys.time())
    one()
    elapsed[[k]] <- as.numeric(Sys.time()) - t0
}
value <- one()
dev.off()
cat(paste(sprintf("%.17g", as.numeric(value)), collapse=","), "\n")
cat(sprintf("%.17g\n", median(elapsed) * 1000))
