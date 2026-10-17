library(blob)
f <- function() as_blob(c("abc", NA_character_))
v <- f()
cat(paste(vapply(v, function(z) if (length(z) == 0) "NA" else paste(as.integer(z), collapse=","), ""), collapse=";"), "\n", sep="")
f()
times <- numeric(20)
for (i in seq_len(20)) { a <- Sys.time(); f(); times[i] <- as.numeric(difftime(Sys.time(), a, units="secs")) * 1000 }
cat(sprintf("r_ms=%.9f\n", median(times)))
