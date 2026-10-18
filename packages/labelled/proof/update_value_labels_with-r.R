suppressPackageStartupMessages(library(labelled))
suppressPackageStartupMessages(library(jsonlite))
one <- function() { d <- data.frame(a=labelled(c(1,2), c(yes=1,no=2))); d <- update_value_labels_with(d, toupper); names(val_labels(d$a)) }
value <- one(); elapsed <- numeric(20)
for (i in seq_len(20)) { t0 <- as.numeric(Sys.time()); one(); elapsed[[i]] <- as.numeric(Sys.time()) - t0 }
cat(sprintf('{"value":%s,"median_ms":%.17g}\n', toJSON(value, auto_unbox=TRUE, null="null", digits=17), median(elapsed)*1000))
