library(labelled)
x <- set_variable_labels(1:3, "demo")
one <- get_label_attribute(x)
t <- numeric(20)
for (i in seq_len(20)) { a <- Sys.time(); set_variable_labels(1:3, "demo"); t[i] <- as.numeric(Sys.time() - a, units = "secs") * 1000 }
cat(sprintf("value=%s\nr_ms=%.17g\n", one, median(t)))
