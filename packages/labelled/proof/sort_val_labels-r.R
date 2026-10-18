suppressPackageStartupMessages(library(labelled))
suppressPackageStartupMessages(library(jsonlite))
one <- function() { x <- labelled(c(1,2,3), c(maybe=2,yes=1,no=3)); names(val_labels(sort_val_labels(x))) }
value <- one(); elapsed <- numeric(20)
for (i in seq_len(20)) { t0 <- as.numeric(Sys.time()); one(); elapsed[[i]] <- as.numeric(Sys.time()) - t0 }
cat(sprintf('{"value":%s,"median_ms":%.17g}\n', toJSON(value, auto_unbox=TRUE, null="null", digits=17), median(elapsed)*1000))
