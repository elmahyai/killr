pkg <- tempfile(); untar("../../../rcran/contrib/htmlTable_2.5.0.tar.gz", exdir=pkg)
source(file.path(pkg, "htmlTable/R/prepGroupCounts.R"))
one <- prepGroupCounts(c(1, 1, 2, 2, 2))
times <- numeric(20)
for (i in seq_len(20)) { t <- Sys.time(); prepGroupCounts(c(1, 1, 2, 2, 2)); times[i] <- as.numeric(Sys.time()-t)*1000 }
cat(sprintf('{"value":%s,"r_ms":%.8f}\n', paste(c(one$n, one$idx, one$names), collapse=","), median(times)))
