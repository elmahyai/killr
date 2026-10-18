suppressPackageStartupMessages(library(labelled))
suppressPackageStartupMessages(library(jsonlite))
one <- function() { x <- labelled(c(1, 9, 2), c(dk=9)); list(as.numeric(val_labels_to_na(x)), length(val_labels(val_labels_to_na(x)))) }
value <- one(); elapsed <- numeric(20)
for (i in seq_len(20)) { t0 <- as.numeric(Sys.time()); one(); elapsed[[i]] <- as.numeric(Sys.time()) - t0 }
cat(sprintf('{"value":%s,"median_ms":%.17g}\n', toJSON(value, auto_unbox=TRUE, null="null", digits=17), median(elapsed)*1000))
