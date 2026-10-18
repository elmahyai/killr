suppressPackageStartupMessages(library(labelled))
suppressPackageStartupMessages(library(jsonlite))
one <- function() { x <- c(1,2); val_labels(set_value_labels(x, one=1, two=2)) }
value <- one(); elapsed <- numeric(20)
for (i in seq_len(20)) { t0 <- as.numeric(Sys.time()); one(); elapsed[[i]] <- as.numeric(Sys.time()) - t0 }
cat(sprintf('{"value":%s,"median_ms":%.17g}\n', toJSON(value, auto_unbox=TRUE, null="null", digits=17), median(elapsed)*1000))
