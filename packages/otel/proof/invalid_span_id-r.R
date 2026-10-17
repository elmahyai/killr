suppressPackageStartupMessages(library(otel))
f <- function() { invalid_span_id }
normalize <- function(x) { if (is.null(x)) return("NULL"); if (is.logical(x)) return(ifelse(x, "True", "False")); if (is.atomic(x)) return(paste(as.character(x), collapse="|")); if (is.list(x) && !is.null(names(x))) return(paste(names(x), collapse="|")); paste(class(x), collapse="|") }
invisible(f())
t <- numeric(20)
for (i in seq_len(20)) { t0 <- Sys.time(); z <- f(); t[i] <- as.numeric(difftime(Sys.time(), t0, units="secs")) }
cat(sprintf("r_ms %.17g\n", median(t)*1000)); cat(normalize(z), "\n")
