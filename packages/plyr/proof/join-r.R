suppressPackageStartupMessages(library(plyr))
stopifnot(identical(as.character(packageVersion("plyr")), "1.8.9"))

n <- 20000L
xid <- ((seq_len(n) - 1L) %% 4000L) + 1L
xv <- seq_len(n) * 0.5
yid <- ((seq_len(n) - 1L) %% 4000L) + 501L
yv <- seq_len(n) * 0.25
x <- data.frame(id = xid, xv = xv)
y <- data.frame(id = yid, yv = yv)

one <- function() join(x, y, by = "id")

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}

show <- function(v) ifelse(is.na(v), "NA", sprintf("%a", v))
shown <- paste(sprintf("%d|%s|%s", value$id, show(value$xv), show(value$yv)), collapse = ";")
cat("VALUE ", shown, "\n", sep = "")
cat(sprintf("MS %.17g\n", median(elapsed) * 1000))
