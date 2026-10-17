suppressPackageStartupMessages(library(survival))

serialize <- function(x) {
  paste(ifelse(is.na(x), "NA", as.character(x)), collapse = ",")
}

one <- function() {
  data1 <- data.frame(
    id = 1:10,
    entry.dt = as.Date(paste("2011", 1:10, "5", sep = "-"))
  )
  temp1 <- c(1, 4, 5, 1, 3, 6, 9, 2, 7, 8, 12, 4, 6, 7, 10, 12, 3)
  data2 <- data.frame(
    id = c(1, 1, 1, 2, 2, 4, 4, 5, 5, 5, 6, 8, 8, 9, 10, 10, 12),
    lab.dt = as.Date(paste("2011", temp1, "1", sep = "-"))
  )
  indx1 <- neardate(data1$id, data2$id, data1$entry.dt, data2$lab.dt)
  indx2 <- neardate(data1$id, data2$id, data1$entry.dt, data2$lab.dt, best = "prior")
  c(serialize(indx1), serialize(indx2))
}

t0 <- as.numeric(Sys.time())
value <- one()
r_untimed <- (as.numeric(Sys.time()) - t0) * 1000

elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
r_median <- median(elapsed) * 1000

cat(paste(value, collapse = "\n"), "\n", sep = "")
cat("R_UNTIMED\n")
cat(sprintf("%.17g\n", r_untimed))
cat("R_MEDIAN\n")
cat(sprintf("%.17g\n", r_median))
