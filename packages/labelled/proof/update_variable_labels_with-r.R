suppressPackageStartupMessages(library(labelled))
suppressPackageStartupMessages(library(jsonlite))
one <- function() { d <- data.frame(a=labelled(1, label="old"), b=labelled(2, label="two")); d <- update_variable_labels_with(d, toupper); c(var_label(d$a),var_label(d$b)) }
value <- one(); elapsed <- numeric(20)
for (i in seq_len(20)) { t0 <- as.numeric(Sys.time()); one(); elapsed[[i]] <- as.numeric(Sys.time()) - t0 }
cat(sprintf('{"value":%s,"median_ms":%.17g}\n', toJSON(value, auto_unbox=TRUE, null="null", digits=17), median(elapsed)*1000))
