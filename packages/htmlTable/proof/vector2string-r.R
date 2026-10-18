pkg <- tempfile(); untar("../../../rcran/contrib/htmlTable_2.5.0.tar.gz", exdir=pkg)
source(file.path(pkg, "htmlTable/R/vector2string.R"))
one <- vector2string(c("a", "b'b", "c"))
times <- numeric(20)
for (i in seq_len(20)) { t <- Sys.time(); vector2string(c("a", "b'b", "c")); times[i] <- as.numeric(Sys.time()-t)*1000 }
cat(jsonlite::toJSON(list(value=one, r_ms=median(times)), auto_unbox=TRUE), "\n")
