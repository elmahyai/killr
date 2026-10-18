library(labelled)
x <- 1:3
attr(x, "label") <- "demo"
one <- label_attribute(x)
t <- numeric(20)
for (i in seq_len(20)) { a <- Sys.time(); label_attribute(x); t[i] <- as.numeric(Sys.time() - a, units = "secs") * 1000 }
cat(sprintf("value=%s\nr_ms=%.17g\n", one, median(t)))
